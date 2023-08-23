from typing import Optional
import traceback

import inflection
from flask import Blueprint, current_app, request, render_template, url_for, jsonify
from notebooker.constants import JobStatus, DEFAULT_RESULT_LIMIT
from notebooker.utils.results import get_all_result_keys
from notebooker.web.utils import get_serializer, get_all_possible_templates

index_bp = Blueprint("index_bp", __name__)


@index_bp.route("/", methods=["GET"])
@index_bp.route("/folder/<path:subfolder>", methods=["GET"])
def index(subfolder: Optional[str] = None):
    """
    The index page which shows cards of each report which has at least one result in the database.
    """
    username = request.headers.get("X-Auth-Username")
    all_reports = get_all_possible_templates()
    with current_app.app_context():
        result = render_template(
            "index.html",
            all_reports=all_reports,
            donevalue=JobStatus.DONE,  # needed so we can check if a result is available
            username=username,
            readonly_mode=current_app.config["READONLY_MODE"],
            scheduler_disabled=current_app.config["DISABLE_SCHEDULER"],
        )
        return result


@index_bp.route("/result_listing/<path:report_name>", methods=["GET"])
def result_listing(report_name):
    """
    The index page which returns a blank table which is async populated by /core/all_available_results.
    Async populating the table from a different URL means that we can lock down the "core" blueprint to
    only users with correct privileges.
    """
    username = request.headers.get("X-Auth-Username")
    result_limit = int(request.args.get("limit") or DEFAULT_RESULT_LIMIT)
    all_reports = get_all_possible_templates()
    with current_app.app_context():
        result = render_template(
            "result_listing.html",
            all_reports=all_reports,
            donevalue=JobStatus.DONE,  # needed so we can check if a result is available
            username=username,
            report_name=report_name,
            result_limit=result_limit,
            n_results_available=get_serializer().n_all_results_for_report_name(report_name),
            titleised_report_name=inflection.titleize(report_name),
            readonly_mode=current_app.config["READONLY_MODE"],
            scheduler_disabled=current_app.config["DISABLE_SCHEDULER"],
        )
        return result
