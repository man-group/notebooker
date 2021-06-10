import json
from typing import Optional, List

from flask import Blueprint, jsonify, render_template, current_app, request

from notebooker.web.handle_overrides import handle_overrides
from notebooker.web.routes.run_report import validate_run_params
from notebooker.web.utils import get_all_possible_templates
from apscheduler.triggers import cron

scheduling_bp = Blueprint("scheduling", __name__)


@scheduling_bp.route("/scheduler")
def scheduler_ui():
    return render_template("scheduler.html", all_reports=get_all_possible_templates())


@scheduling_bp.route("/scheduler/jobs")
def all_schedules():  # TODO: use real data
    jobs = current_app.apscheduler.get_jobs()
    result = []
    for job in jobs:
        result.append(_job_to_json(job))
    return jsonify(result), 200


@scheduling_bp.route("/scheduler/<path:report_name>/<string:job_id>", methods=["DELETE"])
def remove_schedule(report_name, job_id):
    job = current_app.apscheduler.get_job(job_id)
    if job is None or job.kwargs.get("report_name") != report_name:
        return {"status": "Not found"}, 404
    job.remove()

    return "", 200


@scheduling_bp.route("/scheduler/update/<path:report_name>/<string:job_id>", methods=["POST"])
def update_schedule(report_name, job_id):
    job = current_app.apscheduler.get_job(job_id)
    if job is None or job.kwargs.get("report_name") != report_name:
        return {"status": "Not found"}, 404

    issues = []
    trigger = validate_crontab(request.values.get("crontab", ""), issues)
    params = validate_run_params(request.values, issues)
    overrides_dict = handle_overrides(request.values.get("overrides"), issues)
    if issues:
        return jsonify({"status": "Failed", "content": ("\n".join(issues))})

    params = {
        "report_name": report_name,
        "overrides": overrides_dict,
        "report_title": params.report_title,
        "mailto": params.mailto,
        "generate_pdf": params.generate_pdf_output,
        "hide_code": params.hide_code,
    }
    job.modify(trigger=trigger, kwargs=params)

    # Modify won't change the current object, we need to make this change manually so we can display it properly.
    job.trigger = trigger
    job.kwargs = params

    return _job_to_json(job), 200


@scheduling_bp.route("/scheduler/create/<path:report_name>", methods=["POST"])
def create_schedule(report_name):
    if report_name not in get_all_possible_templates():
        return {"status": "Not found"}, 404
    issues = []
    trigger = validate_crontab(request.values.get("crontab", ""), issues)
    params = validate_run_params(request.values, issues)
    overrides_dict = handle_overrides(request.values.get("overrides"), issues)
    if issues:
        return jsonify({"status": "Failed", "content": ("\n".join(issues))})
    params = {
        "report_name": report_name,
        "overrides": overrides_dict,
        "report_title": params.report_title,
        "mailto": params.mailto,
        "generate_pdf": params.generate_pdf_output,
        "hide_code": params.hide_code,
    }
    job = current_app.apscheduler.add_job(
        "notebooker.web.scheduler:run_report",
        jobstore="mongo",
        trigger=trigger,
        kwargs=params,
    )

    return _job_to_json(job), 201


@scheduling_bp.route("/scheduler/hello")
def hello():
    return jsonify(current_app.apscheduler.get_jobs())


def validate_crontab(crontab: str, issues: List[str]) -> cron.CronTrigger:
    parts = crontab.split()
    if len(parts) != 5:
        issues.append("the contrab key must be passed with a string using the crontab(8) format")
    else:
        return cron.CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])

def _job_to_json(job):
     return {
        "id": job.id,
        "trigger": {
            "fields": {field.name: [str(expr) for expr in field.expressions] for field in job.trigger.fields},
        },
        "params": job.kwargs,
        "next_run_time": job.next_run_time.isoformat(),
    }
