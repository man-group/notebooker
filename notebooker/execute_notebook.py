import copy
import datetime
import json
import logging
import os
import subprocess
import traceback
import uuid
from typing import Any, AnyStr, Dict, List, Optional, Union

import papermill as pm
import sys

from notebooker.constants import (
    CANCEL_MESSAGE,
    JobStatus,
    NotebookResultComplete,
    NotebookResultError,
    python_template_dir,
)
from notebooker.serialization.serialization import get_serializer_from_cls
from notebooker.settings import BaseConfig
from notebooker.utils.conversion import _output_ipynb_name, generate_ipynb_from_py, ipython_to_html, ipython_to_pdf
from notebooker.utils.filesystem import initialise_base_dirs
from notebooker.utils.notebook_execution import _output_dir, send_result_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _run_checks(
    job_id: str,
    job_start_time: datetime.datetime,
    template_name: str,
    report_title: str,
    output_base_dir: str,
    template_base_dir: str,
    overrides: Dict[AnyStr, Any],
    generate_pdf_output: Optional[bool] = True,
    hide_code: Optional[bool] = False,
    mailto: Optional[str] = "",
    error_mailto: Optional[str] = "",
    email_subject: Optional[str] = "",
    prepare_only: Optional[bool] = False,
    notebooker_disable_git: bool = False,
    py_template_base_dir: str = "",
    py_template_subdir: str = "",
) -> NotebookResultComplete:
    """
    This is the actual method which executes a notebook, whether running in the webapp or via the entrypoint.
    If this crashes, an exception is raised (and should be caught by run_checks().)

    Parameters
    ----------
    job_id : `str`
        The unique ID of this report.
    job_start_time : `datetime.datetime`
        The UTC start time of this report.
    template_name : `str`
        The name of the template which we are running. NB this should be a path relative to the python_template_dir()
    report_title : `str`
        The user-specified optional title of the report. Defaults to the template name.
    output_base_dir : `str`
        Internal use. The temp directory where output is being saved, local to the executor.
    template_base_dir : `str`
        Internal use. The temp directory where the .py->.ipynb converted templates reside, local to the executor.
    overrides : Dict[AnyStr, Any]
        The dictionary of overrides which parametrize our Notebook Template.
    generate_pdf_output : `Optional[bool]`
        Whether to generate PDF output or not. NB this requires xelatex to be installed on the executor.
    mailto : `Optional[str]`
        Comma-separated email addresses to send on completion (or error).
    prepare_only : `Optional[bool]`
        Internal usage. Whether we want to do everything apart from executing the notebook.


    Returns
    -------
    NotebookResultComplete

    Raises
    ------
    Exception()

    """

    output_dir = _output_dir(output_base_dir, template_name, job_id)
    output_ipynb = _output_ipynb_name(template_name)

    if not os.path.isdir(output_dir):
        logger.info("Making dir @ {}".format(output_dir))
        os.makedirs(output_dir)

    py_template_dir = python_template_dir(py_template_base_dir, py_template_subdir)
    ipynb_raw_path = generate_ipynb_from_py(template_base_dir, template_name, notebooker_disable_git, py_template_dir)
    ipynb_executed_path = os.path.join(output_dir, output_ipynb)

    logger.info("Executing notebook at {} using parameters {} --> {}".format(ipynb_raw_path, overrides, output_ipynb))
    pm.execute_notebook(
        ipynb_raw_path, ipynb_executed_path, parameters=overrides, log_output=True, prepare_only=prepare_only
    )
    with open(ipynb_executed_path, "r") as f:
        raw_executed_ipynb = f.read()

    logger.info("Saving output notebook as HTML from {}".format(ipynb_executed_path))
    html, resources = ipython_to_html(ipynb_executed_path, job_id)
    email_html, resources = ipython_to_html(ipynb_executed_path, job_id, hide_code=hide_code)
    pdf = ipython_to_pdf(raw_executed_ipynb, report_title, hide_code=hide_code) if generate_pdf_output else ""

    notebook_result = NotebookResultComplete(
        job_id=job_id,
        job_start_time=job_start_time,
        job_finish_time=datetime.datetime.now(),
        raw_html_resources=resources,
        raw_ipynb_json=raw_executed_ipynb,
        raw_html=html,
        email_html=email_html,
        mailto=mailto,
        email_subject=email_subject,
        pdf=pdf,
        generate_pdf_output=generate_pdf_output,
        report_name=template_name,
        report_title=report_title,
        overrides=overrides,
    )
    return notebook_result


def run_report(
    job_submit_time,
    report_name,
    overrides,
    result_serializer,
    report_title="",
    job_id=None,
    output_base_dir=None,
    template_base_dir=None,
    attempts_remaining=2,
    mailto="",
    error_mailto="",
    email_subject="",
    generate_pdf_output=True,
    hide_code=False,
    prepare_only=False,
    notebooker_disable_git=False,
    py_template_base_dir="",
    py_template_subdir="",
):

    job_id = job_id or str(uuid.uuid4())
    stop_execution = os.getenv("NOTEBOOKER_APP_STOPPING")
    if stop_execution:
        logger.info("Aborting attempt to run %s, jobid=%s as app is shutting down.", report_name, job_id)
        result_serializer.update_check_status(job_id, JobStatus.CANCELLED, error_info=CANCEL_MESSAGE)
        return
    try:
        logger.info(
            "Calculating a new %s ipynb with parameters: %s (attempts remaining: %s)",
            report_name,
            overrides,
            attempts_remaining,
        )
        result_serializer.update_check_status(
            job_id, report_name=report_name, job_start_time=job_submit_time, status=JobStatus.PENDING
        )
        result = _run_checks(
            job_id,
            job_submit_time,
            report_name,
            report_title,
            output_base_dir,
            template_base_dir,
            overrides,
            mailto=mailto,
            email_subject=email_subject,
            generate_pdf_output=generate_pdf_output,
            hide_code=hide_code,
            prepare_only=prepare_only,
            notebooker_disable_git=notebooker_disable_git,
            py_template_base_dir=py_template_base_dir,
            py_template_subdir=py_template_subdir,
        )
        logger.info("Successfully got result.")
        result_serializer.save_check_result(result)
        logger.info("Saved result to mongo successfully.")
    except Exception:
        error_info = traceback.format_exc()
        logger.exception("%s report failed! (job id=%s)", report_name, job_id)
        result = NotebookResultError(
            job_id=job_id,
            job_start_time=job_submit_time,
            report_name=report_name,
            report_title=report_title,
            error_info=error_info,
            overrides=overrides,
            mailto=error_mailto or mailto,
            generate_pdf_output=generate_pdf_output,
        )
        logger.error(
            "Report run failed. Saving error result to mongo library %s@%s...",
            result_serializer.database_name,
            result_serializer.mongo_host,
        )
        result_serializer.save_check_result(result)
        logger.info("Error result saved to mongo successfully.")
        if attempts_remaining > 0:
            logger.info("Retrying report.")
            return run_report(
                job_submit_time,
                report_name,
                overrides,
                result_serializer,
                report_title=report_title,
                job_id=job_id,
                output_base_dir=output_base_dir,
                template_base_dir=template_base_dir,
                attempts_remaining=attempts_remaining - 1,
                mailto=mailto,
                error_mailto=error_mailto,
                email_subject=email_subject,
                generate_pdf_output=generate_pdf_output,
                hide_code=hide_code,
                prepare_only=prepare_only,
                notebooker_disable_git=notebooker_disable_git,
                py_template_base_dir=py_template_base_dir,
                py_template_subdir=py_template_subdir,
            )
        else:
            logger.info("Abandoning attempt to run report. It failed too many times.")
    return result


def _get_overrides(overrides_as_json: AnyStr, iterate_override_values_of: Optional[AnyStr]) -> List[Dict]:
    """
    Converts input parameters from a JSON string into a list of parameters for reports to be run.
    A list of parameters will return a list of parameters.
    A dictionary of parameters will return:

    * If iterate_override_values_of is set,
      it will return a copy of itself with each value under the iterate_override_values_of key
    * If iterate_override_values_of is not set,
      it will return the dictionary within a list as the only element.
    Parameters
    ----------
    overrides_as_json : `AnyStr`
        A string containing JSON parameters for the report(s) to be run.
    iterate_override_values_of : `Optional[AnyStr]`
        If the overrides are a dictionary, and the dictionary contains this key, the values are exploded out
        into multiple output dictionaries.

    Examples
    --------
    >>> _get_overrides('{"test": [1, 2, 3], "a": 1}', None)
    [{'test': [1, 2, 3], 'a': 1}]
    >>> _get_overrides('{"test": [1, 2, 3], "a": 1}', "test")
    [{"test": 1, "a": 1}, {"test": 2, "a": 1}, {"test": 3, "a": 1}]
    >>> _get_overrides('[{"test": 1, "a": 1}, {"test": 2, "a": 1}, {"test": 3, "a": 1}]', None)
    [{'test': 1, 'a': 1}, {'test': 2, 'a': 1}, {'test': 3, 'a': 1}]
    >>> _get_overrides('[{"test": 1, "a": 1}, {"test": 2, "a": 1}, {"test": 3, "a": 1}]', "blah")
    [{'test': 1, 'a': 1}, {'test': 2, 'a': 1}, {'test': 3, 'a': 1}]

    Returns
    -------
    `List[Dict]`
    The override parameters. Each list item will result in one notebook being run.

    """
    overrides = json.loads(overrides_as_json) if overrides_as_json else {}
    all_overrides = []
    if isinstance(overrides, (list, tuple)):
        if iterate_override_values_of:
            logger.warning(
                "An --iterate-override-values-of has been specified ({}), but a list of overrides ({}) "
                "has been given. We can't use this parameter as expected, but will continue with the "
                "list of overrides.".format(iterate_override_values_of, overrides)
            )
        all_overrides = overrides
    elif iterate_override_values_of:
        if iterate_override_values_of not in overrides:
            raise ValueError(
                "Can't iterate over override values unless it is given in the override json! "
                "Given overrides were: {}".format(overrides)
            )
        to_iterate = overrides[iterate_override_values_of]
        if not isinstance(to_iterate, (list, tuple)):
            raise ValueError(
                "Can't iterate over a non-list or tuple of variables. "
                "The given value was a {} - {}.".format(type(to_iterate), to_iterate)
            )
        for iterated_value in to_iterate:
            new_override = copy.deepcopy(overrides)
            new_override[iterate_override_values_of] = iterated_value
            all_overrides.append(new_override)
    else:
        all_overrides = [overrides]
    return all_overrides


def execute_notebook_entrypoint(
    config: BaseConfig,
    report_name: str,
    overrides_as_json: str,
    iterate_override_values_of: Union[List[str], str],
    report_title: str,
    n_retries: int,
    job_id: str,
    mailto: str,
    error_mailto: str,
    email_subject: str,
    pdf_output: bool,
    hide_code: bool,
    prepare_notebook_only: bool,
):
    report_title = report_title or report_name
    output_dir, template_dir, _ = initialise_base_dirs(output_dir=config.OUTPUT_DIR, template_dir=config.TEMPLATE_DIR)
    all_overrides = _get_overrides(overrides_as_json, iterate_override_values_of)
    notebooker_disable_git = config.NOTEBOOKER_DISABLE_GIT
    py_template_base_dir = config.PY_TEMPLATE_BASE_DIR
    py_template_subdir = config.PY_TEMPLATE_SUBDIR

    start_time = datetime.datetime.now()
    logger.info("Running a report with these parameters:")
    logger.info("report_name = %s", report_name)
    logger.info("overrides_as_json = %s", overrides_as_json)
    logger.info("iterate_override_values_of = %s", iterate_override_values_of)
    logger.info("report_title = %s", report_title)
    logger.info("n_retries = %s", n_retries)
    logger.info("job_id = %s", job_id)
    logger.info("output_dir = %s", output_dir)
    logger.info("template_dir = %s", template_dir)
    logger.info("mailto = %s", mailto)
    logger.info("error_mailto = %s", error_mailto)
    logger.info("email_subject = %s", email_subject)
    logger.info("pdf_output = %s", pdf_output)
    logger.info("hide_code = %s", hide_code)
    logger.info("prepare_notebook_only = %s", prepare_notebook_only)
    logger.info("notebooker_disable_git = %s", notebooker_disable_git)
    logger.info("py_template_base_dir = %s", py_template_base_dir)
    logger.info("py_template_subdir = %s", py_template_subdir)
    logger.info("serializer_cls = %s", config.SERIALIZER_CLS)
    logger.info("serializer_config = %s", config.SERIALIZER_CONFIG)

    logger.info("Calculated overrides are: %s", str(all_overrides))
    result_serializer = get_serializer_from_cls(config.SERIALIZER_CLS, **config.SERIALIZER_CONFIG)
    results = []
    for overrides in all_overrides:
        result = run_report(
            start_time,
            report_name,
            overrides,
            result_serializer,
            report_title=report_title,
            job_id=job_id,
            output_base_dir=output_dir,
            template_base_dir=template_dir,
            attempts_remaining=n_retries - 1,
            mailto=mailto,
            error_mailto=error_mailto,
            email_subject=email_subject,
            generate_pdf_output=pdf_output,
            hide_code=hide_code,
            prepare_only=prepare_notebook_only,
            notebooker_disable_git=notebooker_disable_git,
            py_template_base_dir=py_template_base_dir,
            py_template_subdir=py_template_subdir,
        )
        if result.mailto:
            send_result_email(result, mailto)
        if isinstance(result, NotebookResultError):
            logger.warning("Notebook execution failed! Output was:")
            logger.warning(repr(result))
            raise Exception(result.error_info)
        results.append(result)
    return results


def docker_compose_entrypoint():
    """
    Sadness. This is required because of https://github.com/jupyter/jupyter_client/issues/154
    Otherwise we will get "RuntimeError: Kernel died before replying to kernel_info"
    The suggested fix to use sh -c "command" does not work for our use-case, sadly.

    Examples
    --------
    $ notebooker_execute --report-name watchdog_checks --mongo-host mktdatad
    Received a request to run a report with the following parameters:
    ['/users/is/jbannister/pyenvs/notebooker/bin/python', '-m', 'notebooker.execute_notebook', '--report-name', 'watchdog_checks', '--mongo-host', 'mktdatad']

    $ notebooker_execute
    Received a request to run a report with the following parameters:
    ['/users/is/jbannister/pyenvs/notebooker/bin/python', '-m', 'notebooker.execute_notebook']
    ValueError: Error! Please provide a --report-name.
    """
    args_to_execute = [sys.executable, "-m", __name__] + sys.argv[1:]
    logger.info("Received a request to run a report with the following parameters:")
    logger.info(args_to_execute)
    subprocess.Popen(args_to_execute).wait()
