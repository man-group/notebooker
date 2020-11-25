import json
import os
from logging import getLogger
from typing import Any, Union

from flask import Blueprint, Response, abort, render_template, request, url_for

from notebooker.constants import (
    JobStatus,
    NotebookResultBase,
    NotebookResultComplete,
    NotebookResultError,
    NotebookResultPending,
)
from notebooker.serialization.mongo import _pdf_filename
from notebooker.web.routes.pending_results import task_loading
from notebooker.web.utils import get_serializer, _params_from_request_args, get_all_possible_templates
from notebooker.utils.conversion import get_resources_dir
from notebooker.utils.results import _get_job_results, get_latest_job_results, get_latest_successful_job_results
from notebooker.utils.web import convert_report_name_path_to_url, convert_report_name_url_to_path

serve_results_bp = Blueprint("serve_results_bp", __name__)
logger = getLogger(__name__)


# ------------------- Serving results -------------------- #


def _render_results(job_id: str, report_name: str, result: NotebookResultBase) -> str:
    report_name = convert_report_name_path_to_url(report_name)
    result_url = url_for("serve_results_bp.task_results_html", report_name=report_name, job_id=job_id) if job_id else ""
    ipynb_url = (
        url_for("serve_results_bp.download_ipynb_result", report_name=report_name, job_id=job_id) if job_id else ""
    )
    pdf_url = url_for("serve_results_bp.download_pdf_result", report_name=report_name, job_id=job_id) if job_id else ""
    rerun_url = url_for("run_report_bp.rerun_report", report_name=report_name, job_id=job_id) if job_id else ""
    clone_url = url_for("run_report_bp.run_report_http", report_name=report_name)
    if result and result.overrides:
        clone_url = clone_url + "?json_params={}".format(json.dumps(result.overrides))
    return render_template(
        "results.html",
        job_id=job_id,
        report_name=report_name,
        result=result,
        donevalue=JobStatus.DONE,  # needed so we can check if a result is available
        html_render=result_url,
        ipynb_url=ipynb_url,
        pdf_url=pdf_url,
        rerun_url=rerun_url,
        clone_url=clone_url,
        all_reports=get_all_possible_templates(),
    )


@serve_results_bp.route("/results/<path:report_name>/<job_id>")
def task_results(job_id, report_name):
    """
    Renders the full results page for a given report_name/job_id combination. Most usually accessed from the main page.

    :param job_id: The UUID of the report which we are accessing.
    :param report_name: The name of the report

    :return: The HTML rendering of the results page for a given report_name/job_id combo.
    """
    report_name = convert_report_name_url_to_path(report_name)
    result = _get_job_results(job_id, report_name, get_serializer(), ignore_cache=True)
    return _render_results(job_id, report_name, result)


@serve_results_bp.route("/results/<path:report_name>/latest")
def task_results_latest(report_name):
    """
    Renders the full results page for a report_name. This searches the database
    for the last completed report for the given report_name.

    :param report_name: The name of the report

    :return: The HTML rendering of the results page for the latest successful execution of the given report_name.
    """
    report_name = convert_report_name_url_to_path(report_name)
    params = _params_from_request_args(request.args)
    result = get_latest_job_results(report_name, params, get_serializer())
    job_id = result.job_id
    return _render_results(job_id, report_name, result)


def _process_result_or_abort(result: NotebookResultBase) -> Union[str, Any]:
    if isinstance(result, (NotebookResultError, NotebookResultComplete)):
        return result.raw_html
    if isinstance(result, NotebookResultPending):
        return task_loading(result.report_name, result.job_id)
    abort(404)


@serve_results_bp.route("/result_html_render/<path:report_name>/<job_id>")
def task_results_html(job_id, report_name):
    """
    Returns the HTML render of the .ipynb output of notebook execution. In the webapp this is rendered within an \
    iframe. In this method, we either:

    - present the HTML results, if the job has finished
    - present the error, if the job has failed
    - present the user with some info detailing the progress of the job, if it is still running.

    :param job_id: The UUID of the report which we are accessing.
    :param report_name: The name of the report

    :return: The HTML rendering of the .ipynb for the given report_name & job_id.
    """
    return _process_result_or_abort(_get_job_results(job_id, report_name, get_serializer()))


@serve_results_bp.route("/result_html_render/<path:report_name>/latest")
def latest_parameterised_task_results_html(report_name):
    """
    Returns the HTML render of the .ipynb output of notebook execution. In the webapp this is rendered within an \
    iframe. Searches the database for the last result as of the given date, regardless of status. \
    Notebook parameters can be specified as request args, \
    e.g. ?ticker=AAPL. In this method, we either:

    - present the HTML results, if the job has finished
    - present the error, if the job has failed
    - present the user with some info detailing the progress of the job, if it is still running.

    :param report_name: The name of the report

    :return: The HTML rendering of the .ipynb for the latest successful execution of the given report_name.
    """
    params = _params_from_request_args(request.args)
    result = get_latest_job_results(report_name, params, get_serializer())
    return _process_result_or_abort(result)


@serve_results_bp.route("/result_html_render/as_of/<date:as_of>/<path:report_name>/latest")
def latest_parameterised_task_results_as_of(report_name, as_of):
    """
    Returns the HTML render of the .ipynb output of notebook execution. In the webapp this is rendered within an \
    iframe. Searches the database for the last result as of the given date, regardless of status. \
    Notebook parameters can be specified as request args, \
    e.g. ?ticker=AAPL. In this method, we either:

    - present the HTML results, if the job has finished
    - present the error, if the job has failed
    - present the user with some info detailing the progress of the job, if it is still running.

    :param report_name: The name of the report.
    :param as_of: The maximum date up to which we are searching for any executions.

    :return: The HTML rendering of the .ipynb for the latest execution of the given report_name.
    """
    params = _params_from_request_args(request.args)
    result = get_latest_job_results(report_name, params, get_serializer(), as_of=as_of)
    return _process_result_or_abort(result)


@serve_results_bp.route("/result_html_render/<path:report_name>/latest-all")
def latest_task_results_html(report_name):
    """This URL will ignore all paramterisation of the report and return the latest HTML output \
    of any run for a given report name, regardless of its status. In this method, we either:

     - present the HTML results, if the job has finished
     - present the error, if the job has failed
     - present the user with some info detailing the progress of the job, if it is still running.

    :param report_name: The name of the template which we want to get the latest version of.

    :return: The HTML render of the absolute-latest run of a report, regardless of parametrization.
    """
    return _process_result_or_abort(get_latest_job_results(report_name, None, get_serializer()))


@serve_results_bp.route("/result_html_render/as_of/<date:as_of>/<path:report_name>/latest-all")
def latest_task_results_as_of(report_name, as_of):
    """This URL will ignore all paramterisation of the report and get the latest of any run for a given report name, \
    Up to a given as_of date. In this method, we either:

     - present the HTML results, if the job has finished
     - present the error, if the job has failed
     - present the user with some info detailing the progress of the job, if it is still running.

    :param report_name: The name of the template which we want to get the latest version of, up to and including as_of.
    :param as_of: The maximum date of reports which we want to see.

    :return: The HTML render of the absolute-latest run of a report, regardless of parametrization.
    """
    return _process_result_or_abort(get_latest_job_results(report_name, None, get_serializer(), as_of=as_of))


@serve_results_bp.route("/result_html_render/<path:report_name>/latest-successful")
def latest_successful_task_results_html(report_name):
    """
    Returns the HTML render of the .ipynb output of notebook execution. In the webapp this is rendered within an \
    iframe. Searches the database for the last successful execution of this report_name. \
    Notebook parameters can be specified as request args, \
    e.g. ?ticker=AAPL. In this method, we either:

    - present the HTML results, if the job has finished
    - present the error, if the job has failed
    - present the user with some info detailing the progress of the job, if it is still running.

    :param report_name: The name of the report.

    :return: The HTML rendering of the .ipynb for the latest successful execution of the given report_name.
    """
    params = _params_from_request_args(request.args)
    result = get_latest_successful_job_results(report_name, params, get_serializer())
    return _process_result_or_abort(result)


@serve_results_bp.route("/result_html_render/as_of/<date:as_of>/<path:report_name>/latest-successful")
def latest_successful_task_results_as_of(report_name, as_of):
    """
    Returns the HTML render of the .ipynb output of notebook execution. In the webapp this is rendered within an \
    iframe. Searches the database for the last successful execution as of the given date. \
    Notebook parameters can be specified as request args, \
    e.g. ?ticker=AAPL. In this method, we either:

    - present the HTML results, if the job has finished
    - present the error, if the job has failed
    - present the user with some info detailing the progress of the job, if it is still running.

    :param report_name: The name of the report.
    :param as_of: The maximum date up to which we are searching for any executions.

    :return: The HTML rendering of the .ipynb for the last successful execution of report_name as of the given date.
    """
    params = _params_from_request_args(request.args)
    result = get_latest_successful_job_results(report_name, params, get_serializer(), as_of=as_of)
    return _process_result_or_abort(result)


# ---- Downloads and ancillary data ---- #


@serve_results_bp.route("/result_html_render/<path:report_name>/<job_id>/resources/<path:resource>")
def task_result_resources_html(job_id, resource, report_name):
    """
    Returns resources, such as stylesheets and images, which are requested by the HTML rendering of the .ipynb.

    :param report_name: The name of the report.
    :param resource: The relative path to the resource, as saved on disk during execution and saved into storage.
    :param job_id: The UUID of the report.

    :return: A download of the data as requested. 404s if not found.
    """
    result = _get_job_results(job_id, report_name, get_serializer())
    if isinstance(result, NotebookResultComplete):
        html_resources = result.raw_html_resources
        resource_path = os.path.join(get_resources_dir(job_id), resource)
        if resource_path in html_resources.get("outputs", {}):
            return html_resources["outputs"][resource_path]
    abort(404)


@serve_results_bp.route("/result_download_ipynb/<path:report_name>/<job_id>")
def download_ipynb_result(job_id, report_name):
    """
    Allows a user to download the raw .ipynb output from storage.

    :param report_name: The name of the report.
    :param job_id: The UUID of the report.

    :return: A download of the .ipynb as requested. 404s if not found.
    """
    result = _get_job_results(job_id, report_name, get_serializer())
    if isinstance(result, NotebookResultComplete):
        return Response(
            result.raw_ipynb_json,
            mimetype="application/vnd.jupyter",
            headers={"Content-Disposition": "attachment;filename={}.ipynb".format(job_id)},
        )
    else:
        abort(404)


@serve_results_bp.route("/result_download_pdf/<path:report_name>/<job_id>")
def download_pdf_result(job_id, report_name):
    """
    Allows a user to download the PDF output from storage.

    :param report_name: The name of the report.
    :param job_id: The UUID of the report.

    :return: A download of the PDF as requested. 404s if not found.
    """
    result = _get_job_results(job_id, report_name, get_serializer())
    if isinstance(result, NotebookResultComplete):
        return Response(
            result.pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment;filename={}".format(_pdf_filename(job_id))},
        )
    else:
        abort(404)
