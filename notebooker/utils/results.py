from datetime import datetime as dt
from logging import getLogger
from typing import Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from flask import url_for

from notebooker import constants
from notebooker.exceptions import NotebookRunException
from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.utils.caching import get_cache, get_report_cache, set_cache, set_report_cache
from notebooker.utils.web import convert_report_name_url_to_path

logger = getLogger(__name__)


def _get_job_results(
    job_id: str,
    report_name: str,
    serializer: MongoResultSerializer,
    retrying: Optional[bool] = False,
    ignore_cache: Optional[bool] = False,
) -> constants.NotebookResultBase:
    report_name = convert_report_name_url_to_path(report_name)
    current_result = get_report_cache(report_name, job_id)
    if current_result and not ignore_cache:
        logger.info("Fetched result from cache.")
        notebook_result = current_result
    else:
        notebook_result = serializer.get_check_result(job_id)
        set_report_cache(report_name, job_id, notebook_result)

    if not notebook_result:
        err_info = "Job results not found for report name={} / job id={}. " "Did you use an invalid job ID?".format(
            report_name, job_id
        )
        return constants.NotebookResultError(
            job_id, error_info=err_info, report_name=report_name, job_start_time=dt.now()
        )
    if isinstance(notebook_result, str):
        if not retrying:
            return _get_job_results(job_id, report_name, serializer, retrying=True)
        raise NotebookRunException("An unexpected string was found as a result. Please run your request again.")

    return notebook_result


def _get_results_from_name_and_params(
    job_id_func: Callable[[str, Optional[Dict], Optional[dt]], str],
    report_name: str,
    params: Optional[Mapping],
    serializer: MongoResultSerializer,
    retrying: bool,
    ignore_cache: bool,
    as_of: Optional[dt] = None,
) -> constants.NotebookResultBase:
    report_name = convert_report_name_url_to_path(report_name)
    latest_job_id = job_id_func(report_name, params, as_of)
    if not latest_job_id:
        err_info = "No job results found for report name={} with params={} as of {}".format(report_name, params, as_of)
        return constants.NotebookResultError(
            latest_job_id, error_info=err_info, report_name=report_name, overrides=params, job_start_time=dt.now()
        )
    return _get_job_results(latest_job_id, report_name, serializer, retrying, ignore_cache)


def get_latest_job_results(
    report_name: str,
    params: Optional[Mapping],
    serializer: MongoResultSerializer,
    retrying: bool = False,
    ignore_cache: bool = False,
    as_of: Optional[dt] = None,
) -> constants.NotebookResultBase:
    report_name = convert_report_name_url_to_path(report_name)
    return _get_results_from_name_and_params(
        serializer.get_latest_job_id_for_name_and_params, report_name, params, serializer, retrying, ignore_cache, as_of
    )


def get_latest_successful_job_results(
    report_name: str,
    params: Optional[Mapping],
    serializer: MongoResultSerializer,
    retrying: bool = False,
    ignore_cache: bool = False,
    as_of: Optional[dt] = None,
) -> constants.NotebookResultBase:
    return _get_results_from_name_and_params(
        serializer.get_latest_successful_job_id_for_name_and_params,
        report_name,
        params,
        serializer,
        retrying,
        ignore_cache,
        as_of,
    )


def get_all_result_keys(
    serializer: MongoResultSerializer, limit: int = 0, force_reload: bool = False
) -> List[Tuple[str, str]]:
    all_keys = get_cache(("all_result_keys", limit))
    if not all_keys or force_reload:
        all_keys = serializer.get_all_result_keys(limit=limit)
        set_cache(("all_result_keys", limit), all_keys, timeout=1)
    return all_keys


def get_all_available_results_json(serializer: MongoResultSerializer, limit: int) -> List[constants.NotebookResultBase]:
    json_output = []
    for result in serializer.get_all_results(limit=limit, load_payload=False):
        output = result.saveable_output()
        output["result_url"] = url_for(
            "serve_results_bp.task_results", job_id=output["job_id"], report_name=output["report_name"]
        )
        output["ipynb_url"] = url_for(
            "serve_results_bp.download_ipynb_result", job_id=output["job_id"], report_name=output["report_name"]
        )
        output["pdf_url"] = url_for(
            "serve_results_bp.download_pdf_result", job_id=output["job_id"], report_name=output["report_name"]
        )
        output["rerun_url"] = url_for(
            "run_report_bp.rerun_report", job_id=output["job_id"], report_name=output["report_name"]
        )
        json_output.append(output)
    return json_output


def get_latest_successful_job_results_all_params(
    report_name: str,
    serializer: MongoResultSerializer,
    retrying: Optional[bool] = False,
    ignore_cache: Optional[bool] = False,
) -> Iterator[constants.NotebookResultComplete]:
    for job_id in serializer.get_latest_successful_job_ids_for_name_all_params(report_name):
        yield _get_job_results(job_id, report_name, serializer, retrying, ignore_cache)
