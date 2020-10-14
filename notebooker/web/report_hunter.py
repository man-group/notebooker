import datetime
import os
import time
from logging import getLogger

from notebooker.constants import RUNNING_TIMEOUT, SUBMISSION_TIMEOUT, JobStatus
from notebooker.serialization.serialization import initialize_serializer_from_config
from notebooker.utils.caching import get_report_cache, set_report_cache
from notebooker.settings import WebappConfig

logger = getLogger(__name__)


def _report_hunter(webapp_config: WebappConfig, run_once: bool = False, timeout: int = 5):
    """
    This is a function designed to run in a thread alongside the webapp. It updates the cache which the
    web app reads from and performs some admin on pending/running jobs. The function terminates either when
    run_once is set to True, or the "NOTEBOOKER_APP_STOPPING" environment variable is set.
    :param serializer_cls:
        The name of the serialiser (as acquired from Serializer.SERIALIZERNAME.value)
    :param run_once:
        Whether to infinitely run this function or not.
    :param timeout:
        The time in seconds that we cache results.
    :param serializer_kwargs:
        Any kwargs which are required for a Serializer to be initialised successfully.
    """
    serializer = initialize_serializer_from_config(webapp_config)
    last_query = None
    while not os.getenv("NOTEBOOKER_APP_STOPPING"):
        try:
            ct = 0
            # Now, get all pending requests and check they haven't timed out...
            all_pending = serializer.get_all_results(
                mongo_filter={"status": {"$in": [JobStatus.SUBMITTED.value, JobStatus.PENDING.value]}}
            )
            now = datetime.datetime.now()
            cutoff = {
                JobStatus.SUBMITTED: now - datetime.timedelta(minutes=SUBMISSION_TIMEOUT),
                JobStatus.PENDING: now - datetime.timedelta(minutes=RUNNING_TIMEOUT),
            }
            for result in all_pending:
                this_cutoff = cutoff.get(result.status)
                if result.job_start_time <= this_cutoff:
                    delta_seconds = (now - this_cutoff).total_seconds()
                    serializer.update_check_status(
                        result.job_id,
                        JobStatus.TIMEOUT,
                        error_info="This request timed out while being submitted to run. "
                        "Please try again! Timed out after {:.0f} minutes "
                        "{:.0f} seconds.".format(delta_seconds / 60, delta_seconds % 60),
                    )
            # Finally, check we have the latest updates
            _last_query = datetime.datetime.now() - datetime.timedelta(minutes=1)
            query_results = serializer.get_all_results(since=last_query)
            for result in query_results:
                ct += 1
                existing = get_report_cache(result.report_name, result.job_id, cache_dir=webapp_config.CACHE_DIR)
                if not existing or result.status != existing.status:  # Only update the cache when the status changes
                    set_report_cache(
                        result.report_name, result.job_id, result, timeout=timeout, cache_dir=webapp_config.CACHE_DIR
                    )
                    logger.info(
                        "Report-hunter found a change for {} (status: {}->{})".format(
                            result.job_id, existing.status if existing else None, result.status
                        )
                    )
            logger.info("Found {} updates since {}.".format(ct, last_query))
            last_query = _last_query
        except Exception as e:
            logger.exception(str(e))
        if run_once:
            break
        time.sleep(10)
    logger.info("Report-hunting thread successfully killed.")
