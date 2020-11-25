import traceback

from flask import Blueprint, current_app, request, render_template, url_for, jsonify
from notebooker.constants import JobStatus
from notebooker.utils.results import get_all_result_keys
from notebooker.web.utils import get_serializer, get_all_possible_templates

index_bp = Blueprint("index_bp", __name__)


@index_bp.route("/", methods=["GET"])
def index():
    """
    The index page which returns a blank table which is async populated by /core/all_available_results.
    Async populating the table from a different URL means that we can lock down the "core" blueprint to
    only users with correct privileges.
    """
    username = request.headers.get("X-Auth-Username")
    all_reports = get_all_possible_templates()
    with current_app.app_context():
        result = render_template(
            "index.html",
            all_jobs_url=url_for("core_bp.all_available_results"),
            all_reports=all_reports,
            n_results_available=get_serializer().n_all_results(),
            donevalue=JobStatus.DONE,  # needed so we can check if a result is available
            username=username,
        )
        return result


@index_bp.route("/delete_report/<job_id>", methods=["POST"])
def delete_report(job_id):
    """
    Deletes a report from the underlying storage. Only marks as "status=deleted" so the report is retrievable \
    at a later date.

    :param job_id: The UUID of the report to delete.

    :return: A JSON which contains "status" which will either be "ok" or "error".
    """
    try:
        get_serializer().delete_result(job_id)
        get_all_result_keys(get_serializer(), limit=50, force_reload=True)
        result = {"status": "ok"}
    except Exception:
        error_info = traceback.format_exc()
        result = {"status": "error", "error": error_info}
    return jsonify(result)
