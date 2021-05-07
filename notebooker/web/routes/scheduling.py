from flask import Blueprint, jsonify, render_template, current_app

from notebooker.web.utils import get_all_possible_templates
from apscheduler.triggers import cron

scheduling_bp = Blueprint("scheduling", __name__)


@scheduling_bp.route("/scheduler")
def scheduler_ui():
    return render_template("scheduler.html", all_reports=get_all_possible_templates())


@scheduling_bp.route("/scheduler/jobs")
def all_schedules():  # TODO: use real data
    return jsonify(
        [
            {
                "id": "Notebook1Morning",
                "func": "execute_notebook:main",
                "trigger": "date",
                "status": "Successful",
                "run_date": "2025-12-01T12:30:01+00:00",
            },
            {
                "id": "Notebook1Evening",
                "func": "execute_notebook:main",
                "trigger": "date",
                "status": "Failed",
                "run_date": "2020-06-01T18:29:01+00:00",
            },
            {
                "id": "DifferentNotebook",
                "func": "execute_notebook:main",
                "trigger": "date",
                "status": "Successful",
                "run_date": "2023-04-01T12:11:01+00:00",
            },
        ]
    )


@scheduling_bp.route("/scheduler/create_schedule", methods=["POST"])
def create_schedule():
    crontab = "* * * * *"
    parts = crontab.split()
    current_app.apscheduler.add_job(
        "notebooker.web.scheduler:run_report",
        jobstore="mongo",
        trigger=cron.CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]),
        kwargs={
            "report_name": "sample/plot_random",
            "overrides": {},
            "report_title": "schedule_test",
            "mailto": "",
            "generate_pdf": False,
            "hide_code": True,
        },
    )
    return 200


@scheduling_bp.route("/scheduler/hello")
def hello():
    return jsonify(current_app.apscheduler.get_jobs())
