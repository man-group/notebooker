from flask import render_template, url_for, jsonify, Blueprint, request

from notebooker.constants import JobStatus
from notebooker.utils.results import _get_job_results, get_latest_job_results
from notebooker.web.utils import get_serializer, _params_from_request_args

pending_results_bp = Blueprint("pending_results_bp", __name__)


def task_loading(report_name, job_id):
    """ Loaded once, when the user queries /results/<report_name>/<job_id> and it is pending. """
    return render_template(
        "loading.html",
        job_id=job_id,
        location=url_for("pending_results_bp.task_status", report_name=report_name, job_id=job_id),
    )


def _get_job_status(job_id, report_name):
    """
    Continuously polled for updates by the user client, until the notebook has completed execution (or errored).
    """
    job_result = _get_job_results(job_id, report_name, get_serializer(), ignore_cache=True)
    if job_result is None:
        return {"status": "Job not found. Did you use an old job ID?"}
    if job_result.status in (JobStatus.DONE, JobStatus.ERROR, JobStatus.TIMEOUT, JobStatus.CANCELLED):
        response = {
            "status": job_result.status.value,
            "results_url": url_for("serve_results_bp.task_results", report_name=report_name, job_id=job_id),
        }
    else:
        response = {"status": job_result.status.value, "run_output": "\n".join(job_result.stdout)}
    return response


@pending_results_bp.route("/status/<path:report_name>/<job_id>")
def task_status(report_name, job_id):
    """
    Returns the status of a given report. If it is no longer running, a results_url is provided which should show
    the HTML output of the report (regardless of whether it succeeded or failed.)

    :param report_name: The name of the report which we are running.
    :param job_id: The UUID of the job which we ran.

    :return: A JSON which contains "status" and either stdout in "run_output" or a URL to results in "results_url".
    """
    return jsonify(_get_job_status(job_id, report_name))


@pending_results_bp.route("/status/<path:report_name>/latest")
def task_latest_status(report_name):
    """
    Searches for the latest status of the given report_name/override args combination, and returns the status with
    a redirect URL or stdout.

    :param report_name: The name of the report which we are searching for the latest status of.

    :return: A JSON which contains "status" and either stdout in "run_output" or a URL to results in "results_url".
    """
    params = _params_from_request_args(request.args)
    result = get_latest_job_results(report_name, params, get_serializer())
    job_id = result.job_id
    if job_id:
        return jsonify(_get_job_status(job_id, report_name))
    return jsonify({"status": "Job not found for given overrides"})
