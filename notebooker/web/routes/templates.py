from typing import Optional

from flask import jsonify, Blueprint

from notebooker.utils.results import get_count_and_latest_time_per_report
from notebooker.utils.web import convert_report_name_url_to_path
from notebooker.web.routes.report_execution import get_report_parameters_html
from notebooker.web.utils import all_templates_flattened, get_all_possible_templates, get_serializer

templates_bp = Blueprint("templates_bp", __name__)


@templates_bp.route("/core/get_all_templates_with_results/folder/")
@templates_bp.route("/core/get_all_templates_with_results/folder/<path:subfolder>")
def all_available_templates_with_results(subfolder: Optional[str] = None):
    """
    Core function for the index.html view which shows the templates which have results available.

    :returns: A JSON containing a list of template names with a count of how many results are in each.
    """
    return jsonify(get_count_and_latest_time_per_report(get_serializer(), subfolder))


@templates_bp.route("/core/all_possible_templates")
def get_all_possible_templates_url():
    """
    Core function which populates the sidebar listing of possible reports which a user can execute from the webapp.
    Called on pretty much every user-facing page.
    The structure is recursive in its nature, and therefore if a node points to None/undefined then it is treated as
    a leaf node.

    :returns: A JSON which points from a report name to either its children or None if it is a leaf node.
    """
    return jsonify(get_all_possible_templates())


@templates_bp.route("/core/all_possible_templates_flattened")
def all_possible_templates_flattened():
    """
    Core function which returns a flattened list of possible reports which a user can execute from the webapp.

    :returns: A JSON which is a list of all possible templates with their full names.
    """
    return jsonify({"result": all_templates_flattened()})


@templates_bp.route("/core/get_template_parameters/<path:report_name>", methods=["GET"])
def get_template_parameters(report_name):
    """
    Get the parameters of the Notebook Template which is about to be executed in Python.

    :param report_name: The parameter here should be a "/"-delimited string which mirrors the directory structure of \
        the notebook templates.

    :returns: Get the parameters of the Notebook Template which is about to be executed in Python syntax.
    """
    report_name = convert_report_name_url_to_path(report_name)
    params_as_html = get_report_parameters_html(report_name)
    return jsonify({"result": params_as_html}) if params_as_html else ("", 404)
