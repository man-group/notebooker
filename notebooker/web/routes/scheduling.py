from flask import Blueprint, jsonify, render_template

from notebooker.web.utils import get_all_possible_templates

scheduling_bp = Blueprint("scheduling", __name__)


@scheduling_bp.route("/scheduler")
def scheduler_ui():
    return render_template("scheduler.html", all_reports=get_all_possible_templates())


@scheduling_bp.route("/scheduler/jobs")
def all_schedules():
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
