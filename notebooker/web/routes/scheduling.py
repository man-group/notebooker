import json
from typing import Optional, List
import uuid

from apscheduler.jobstores.base import ConflictingIdError
from flask import Blueprint, jsonify, render_template, current_app, request, url_for, abort

from notebooker.utils.web import json_to_python
from notebooker.web.handle_overrides import handle_overrides
from notebooker.web.routes.run_report import validate_run_params
from notebooker.web.utils import get_all_possible_templates, all_templates_flattened
from apscheduler.triggers import cron

scheduling_bp = Blueprint("scheduling_bp", __name__)


@scheduling_bp.route("/scheduler/health")
def scheduler_is_up():
    if not hasattr(current_app, "apscheduler") or current_app.apscheduler is None:
        abort(404)
    return jsonify({"status": "OK"})  # TODO: Add an actual health check here


@scheduling_bp.route("/scheduler")
def scheduler_ui():
    return render_template("scheduler.html", all_reports=get_all_possible_templates())


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
    return f"{report_name}_{report_title}"


@scheduling_bp.route("/scheduler/update/<path:report_name>", methods=["POST"])
def update_schedule(report_name):
    issues = []
    params = validate_run_params(request.values, issues)
    job_id = get_job_id(report_name, params.report_title)
    job = current_app.apscheduler.get_job(job_id)
    if job is None or job.kwargs.get("report_name") != report_name:
        return jsonify({"status": "Not found"}), 404
    print(request.values)
    trigger = validate_crontab(request.values.get("cron_schedule", ""), issues)
    overrides_dict = handle_overrides(request.values.get("overrides", ""), issues)
    if issues:
        return jsonify({"status": "Failed", "content": ("\n".join(issues))})

    params = {
        "report_name": report_name,
        "overrides": overrides_dict,
        "report_title": params.report_title,
        "mailto": params.mailto,
        "generate_pdf": params.generate_pdf_output,
        "hide_code": params.hide_code,
        "scheduler_job_id": job_id,
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
    params = validate_run_params(request.values, issues)
    overrides_dict = handle_overrides(request.values.get("overrides", ""), issues)
    if issues:
        return jsonify({"status": "Failed", "content": ("\n".join(issues))})
    job_id = get_job_id(report_name, params.report_title)
    dict_params = {
        "report_name": report_name,
        "overrides": overrides_dict,
        "report_title": params.report_title,
        "mailto": params.mailto,
        "generate_pdf": params.generate_pdf_output,
        "hide_code": params.hide_code,
        "scheduler_job_id": job_id,
    }
    try:
        job = current_app.apscheduler.add_job(
            "notebooker.web.scheduler:run_report", jobstore="mongo", trigger=trigger, kwargs=dict_params, id=job_id
        )

        return jsonify(_job_to_json(job)), 201
    except ConflictingIdError as e:
        return jsonify({"status": "Failed", "content": str(e)})


def validate_crontab(crontab: str, issues: List[str]) -> cron.CronTrigger:
    parts = crontab.split()
    if len(parts) != 5:
        issues.append("The crontab key must be passed with a string using 5 crontab parts")
    else:
        return cron.CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])


def trigger_to_crontab(trigger: cron.CronTrigger) -> str:
    fields = {f.name: str(f) for f in trigger.fields}
    return f"{fields['minute']} {fields['hour']} {fields['day']} {fields['month']} {fields['day_of_week']}"


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
