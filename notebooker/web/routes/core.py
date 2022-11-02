from pathlib import Path
from flask import Blueprint, jsonify, request

import notebooker.version
from notebooker.constants import DEFAULT_RESULT_LIMIT
from notebooker.utils.results import get_all_available_results_json, get_count_and_latest_time_per_report
from notebooker.web.utils import _get_python_template_dir, get_serializer, get_all_possible_templates, all_templates_flattened

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
    return jsonify(get_all_available_results_json(get_serializer(), limit, report_name=report_name))


@core_bp.route("/core/get_all_templates_with_results")
def all_available_templates_with_results():
    """
    Core function for the index.html view which shows the templates which have results available.

    :returns: A JSON containing a list of template names with a count of how many results are in each.
    """
    return jsonify(get_count_and_latest_time_per_report(get_serializer()))


@core_bp.route("/core/all_possible_templates")
def get_all_possible_templates_url():
    """
    Core function which populates the sidebar listing of possible reports which a user can execute from the webapp.
    Called on pretty much every user-facing page.
    The structure is recursive in its nature, and therefore if a node points to None/undefined then it is treated as
    a leaf node.

    :returns: A JSON which points from a report name to either its children or None if it is a leaf node.
    """
    return jsonify(get_all_possible_templates())


@core_bp.route("/core/all_possible_templates_flattened")
def all_possible_templates_flattened():
    """
    Core function which returns a flattened list of possible reports which a user can execute from the webapp.

    :returns: A JSON which is a list of all possible templates with their full names.
    """
    return jsonify({"result": all_templates_flattened()})


@core_bp.route("/core/version")
def get_version_no():
    """
    Core function which returns the Notebooker version number.

    :returns: A JSON mapping from "version" to the string repr of the version number.
    """
    return jsonify({"version": notebooker.version.__version__})


@core_bp.route("/core/notebook/upload", methods=["POST"])
def upload_notebook():
    """
    Stores a notebook in git
    """
    templates = Path(_get_python_template_dir())
    web = templates / "web"
    web.mkdir(exist_ok=True)
    notebook_name = request.values.get("name")
    if not notebook_name or not notebook_name.endswith(".ipynb"):
        return jsonify({"status": "Invalid notebook name"}), 400
    with open(web / request.values.get("name"), "w") as fp:
        fp.write(request.values.get("notebook", ""))
    return jsonify({"status": "Notebook uploaded"})
