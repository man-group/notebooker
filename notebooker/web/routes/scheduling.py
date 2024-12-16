import json
from typing import Optional, List, Callable
import logging

from apscheduler.jobstores.base import ConflictingIdError
from flask import Blueprint, jsonify, render_template, current_app, request, url_for, abort

from notebooker.utils.web import json_to_python
from notebooker.web.handle_overrides import handle_overrides
from notebooker.web.routes.report_execution import validate_run_params
from notebooker.web.utils import get_all_possible_templates, all_templates_flattened
from apscheduler.triggers import cron

scheduling_bp = Blueprint("scheduling_bp", __name__)
logger = logging.getLogger(__name__)


@scheduling_bp.route("/scheduler/health")
def scheduler_is_up():
    if not hasattr(current_app, "apscheduler") or current_app.apscheduler is None:
        abort(404)
    return jsonify({"status": "OK"})  # TODO: Add an actual health check here


@scheduling_bp.route("/scheduler")
def scheduler_ui():
    return render_template(
        "scheduler.html",
        all_reports=get_all_possible_templates(),
        default_mailfrom=current_app.config["DEFAULT_MAILFROM"],
        readonly_mode=current_app.config["READONLY_MODE"],
        scheduler_disabled=current_app.config["DISABLE_SCHEDULER"],
    )


@scheduling_bp.route("/scheduler/jobs")
def all_schedules():
    jobs = current_app.apscheduler.get_jobs()
    result = []
    for job in jobs:
        result.append(_job_to_json(job))
    return jsonify(result), 200


@scheduling_bp.route("/scheduler/<path:job_id>", methods=["DELETE"])
def remove_schedule(job_id):
    job = current_app.apscheduler.get_job(job_id)
    if job is None:
        return jsonify({"status": "Not found"}), 404
    job.remove()
    return jsonify({"status": "Complete"}), 200


def get_job_id(report_name: str, report_title: str) -> str:
    if "PATH_TO_CATEGORY_DICT" in current_app.config and report_name in current_app.config["PATH_TO_CATEGORY_DICT"]:
        report_name = current_app.config["PATH_TO_CATEGORY_DICT"][report_name] + "/" + report_name.split("/")[-1]
    return f"{report_name}_{report_title}"


@scheduling_bp.route("/scheduler/update/<path:report_name>", methods=["POST"])
def update_schedule(report_name):
    issues = []
    params = validate_run_params(report_name, request.values, issues)
    job_id = get_job_id(report_name, params.report_title)
    job = current_app.apscheduler.get_job(job_id)
    if job is None or job.kwargs.get("report_name") != report_name:
        return jsonify({"status": "Not found"}), 404
    print(request.values)
    trigger = validate_crontab(request.values.get("cron_schedule", ""), issues)
    overrides_dict = handle_overrides(request.values.get("overrides", ""), issues)
    if issues:
        return jsonify({"status": "Failed", "content": ("\n".join(issues))})
    if "PATH_TO_CATEGORY_DICT" in current_app.config and report_name in current_app.config["PATH_TO_CATEGORY_DICT"]:
        category = current_app.config["PATH_TO_CATEGORY_DICT"][report_name]
    else:
        category = ""
    params = {
        "report_name": report_name,
        "overrides": overrides_dict,
        "report_title": params.report_title,
        "mailto": params.mailto,
        "error_mailto": params.error_mailto,
        "mailfrom": params.mailfrom,
        "email_subject": params.email_subject,
        "generate_pdf": params.generate_pdf_output,
        "hide_code": params.hide_code,
        "is_slideshow": params.is_slideshow,
        "scheduler_job_id": job_id,
        "category": category,
    }
    job.modify(trigger=trigger, kwargs=params)
    current_app.apscheduler.reschedule_job(job_id, jobstore="mongo", trigger=trigger)

    # job.modify won't change the current object, so we need to do it manually before converting to json
    job.trigger = trigger
    job.kwargs = params

    return jsonify(_job_to_json(job)), 200


@scheduling_bp.route("/scheduler/create/<path:report_name>", methods=["POST"])
def create_schedule(report_name):
    if report_name not in all_templates_flattened():
        return jsonify({"status": "Not found"}), 404
    issues = []
    trigger = validate_crontab(request.values.get("cron_schedule", ""), issues)
    params = validate_run_params(report_name, request.values, issues)
    overrides_dict = handle_overrides(request.values.get("overrides", ""), issues)
    if issues:
        return jsonify({"status": "Failed", "content": ("\n".join(issues))})
    job_id = get_job_id(report_name, params.report_title)
    if "PATH_TO_CATEGORY_DICT" in current_app.config and report_name in current_app.config["PATH_TO_CATEGORY_DICT"]:
        category = current_app.config["PATH_TO_CATEGORY_DICT"][report_name]
    else:
        category = ""
    dict_params = {
        "report_name": report_name,
        "overrides": overrides_dict,
        "report_title": params.report_title,
        "mailto": params.mailto,
        "error_mailto": params.error_mailto,
        "mailfrom": params.mailfrom,
        "email_subject": params.email_subject,
        "generate_pdf": params.generate_pdf_output,
        "hide_code": params.hide_code,
        "scheduler_job_id": job_id,
        "is_slideshow": params.is_slideshow,
        "category": category,
    }
    logger.info(f"Creating job with params: {dict_params}")
    try:
        job = current_app.apscheduler.add_job(
            "notebooker.web.scheduler:run_report", jobstore="mongo", trigger=trigger, kwargs=dict_params, id=job_id
        )

        return jsonify(_job_to_json(job)), 201
    except ConflictingIdError as e:
        return jsonify({"status": "Failed", "content": str(e)})


def _convert_day_of_week(day_of_week: str, convert_func: Callable) -> str:
    """
    Given we are providing a crontab converts the int-based day specification according to the function passed.
    Does not shift char-based descriptors i.e. 'MON-FRI'.
    Parameters
    ----------
    day_of_week - str - "FRI", "MON-FRI", "1"(UNIX Monday)
    convert_func - function to use for conversion
    """

    def shift(mychar):
        if mychar.isnumeric():
            myint = int(mychar)
            return str(convert_func(myint))
        else:
            return mychar

    return "".join([shift(char) for char in day_of_week])


def crontab_to_apscheduler_day_of_week(day_of_week: str) -> str:
    """
    Converts UNIX standard days-of-week (SUN=0, MON=1, ...) to APScheduler ones (MON=0, TUE=1, ...)
    """
    return _convert_day_of_week(day_of_week, lambda dow: (dow + 6) % 7)


def apscheduler_to_crontab_day_of_week(day_of_week: str) -> str:
    """
    Converts APScheduler days-of-week (MON=0, TUE=1, ...) to UNIX standard ones (SUN=0, MON=1, ...)
    """
    return _convert_day_of_week(day_of_week, lambda dow: (dow - 6) % 7)


def validate_crontab(crontab: str, issues: List[str]) -> cron.CronTrigger:
    parts = crontab.split()
    if len(parts) != 5:
        issues.append("The crontab key must be passed with a string using 5 crontab parts")
    else:
        parts[4] = crontab_to_apscheduler_day_of_week(parts[4])
        return cron.CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])


def trigger_to_crontab(trigger: cron.CronTrigger) -> str:
    fields = {f.name: str(f) for f in trigger.fields}
    day_of_week = apscheduler_to_crontab_day_of_week(fields["day_of_week"])
    return f"{fields['minute']} {fields['hour']} {fields['day']} {fields['month']} {day_of_week}"


def _job_to_json(job):
    kwargs = job.kwargs
    kwargs["overrides"] = json_to_python(json.dumps(job.kwargs["overrides"]))
    return {
        "id": job.id,
        "trigger": {"fields": {field.name: [str(expr) for expr in field.expressions] for field in job.trigger.fields}},
        "params": job.kwargs,
        "cron_schedule": trigger_to_crontab(job.trigger),
        "next_run_time": job.next_run_time.isoformat(),
        "delete_url": url_for("scheduling_bp.remove_schedule", job_id=job.id),
    }
