from flask import Blueprint, jsonify, request

from notebooker.utils.results import get_all_available_results_json
from notebooker.web.utils import get_serializer, get_all_possible_templates

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
    Defaults to the top 50 results.

    :returns: A JSON containing a list of results. The actual payload data is substituted with URLs that would \
    kick off a download, if requested.
    """
    limit = int(request.args.get("limit", 50))
    return jsonify(get_all_available_results_json(get_serializer(), limit))


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
