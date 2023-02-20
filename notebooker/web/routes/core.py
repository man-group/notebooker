from flask import Blueprint, jsonify, request, current_app

import notebooker.version
from notebooker.constants import DEFAULT_RESULT_LIMIT
from notebooker.utils.results import get_all_available_results_json
from notebooker.web.utils import get_serializer

core_bp = Blueprint("core_bp", __name__)


@core_bp.route("/core/user_profile")
def user_profile():
    """
    A helper URL which returns the user profile as specified by the incoming headers.
    Useful if running the webapp behind an OAuth proxy which provides these headers.

    :returns: A JSON of the available user information.
    """
    user_roles = request.headers.get("X-Auth-Roles")
    username = request.headers.get("X-Auth-Username")
    return jsonify({"username": username, "roles": user_roles})


@core_bp.route("/core/get_all_available_results")
def all_available_results():
    """
    Core function for the homepage/index page which returns all available results.
    Defaults to the top DEFAULT_RESULT_LIMIT results.

    :returns: A JSON containing a list of results. The actual payload data is substituted with URLs that would \
    kick off a download, if requested.
    """
    limit = int(request.args.get("limit") or DEFAULT_RESULT_LIMIT)
    report_name = request.args.get("report_name")
    with current_app.app_context():
        return jsonify(
            get_all_available_results_json(
                get_serializer(), limit, report_name=report_name, readonly_mode=current_app.config["READONLY_MODE"]
            )
        )


@core_bp.route("/core/version")
def get_version_no():
    """
    Core function which returns the Notebooker version number.

    :returns: A JSON mapping from "version" to the string repr of the version number.
    """
    return jsonify({"version": notebooker.version.__version__})
