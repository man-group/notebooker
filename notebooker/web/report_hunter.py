import datetime
import os
import time
from logging import getLogger

from notebooker.constants import SUBMISSION_TIMEOUT, JobStatus
from notebooker.serialization.serialization import initialize_serializer_from_config
from notebooker.utils.caching import get_report_cache, set_report_cache
from notebooker.settings import WebappConfig

logger = getLogger(__name__)


def try_register_success_prometheus(report_name: str, report_title: str):
    try:
        from notebooker.web.routes.prometheus import record_successful_report

        record_successful_report(report_name, report_title)
    except ImportError as e:
        logger.info(f"Attempted to log success to prometheus but failed with ImportError({e}).")


def try_register_fail_prometheus(report_name: str, report_title: str):
    try:
        from notebooker.web.routes.prometheus import record_failed_report

        record_failed_report(report_name, report_title)
    except ImportError as e:
        logger.info(f"Attempted to log failure to prometheus but failed with ImportError({e}).")


class LRUSet(object):
    """
    A simple implementation of a least-recently-used cache, but with O(1) lookup.
    """

    def __init__(self, max_size: int):
        self.max_size = max_size
        self._linked_list_members = []
        self._hashed_members = set()

    def add(self, item):
        self._hashed_members.add(item)
        self._linked_list_members.append(item)
        if len(self._linked_list_members) > self.max_size:
            removed = self._linked_list_members.pop(0)
            self._hashed_members.remove(removed)

    def remove(self, item):
        if item in self._hashed_members:
            self._hashed_members.remove(item)
            self._linked_list_members.remove(item)

    def __contains__(self, item):
        return self._hashed_members.__contains__(item)

    def __iter__(self):
        yield from iter(self._linked_list_members)

    def __len__(self):
        return len(self._linked_list_members)


def _report_hunter(webapp_config: WebappConfig, run_once: bool = False, timeout: int = 120):
    """
    This is a function designed to run in a thread alongside the webapp. It updates the cache which the
    web app reads from and performs some admin on pending/running jobs. The function terminates either when
    run_once is set to True, or the "NOTEBOOKER_APP_STOPPING" environment variable is set.
    :param serializer_cls:
        The name of the serialiser (as acquired from Serializer.SERIALIZERNAME.value)
    :param run_once:
        Whether to infinitely run this function or not.
    :param timeout:
        The time in seconds that we cache results. Defaults to 120s.
    :param serializer_kwargs:
        Any kwargs which are required for a Serializer to be initialised successfully.
    """
    serializer = initialize_serializer_from_config(webapp_config)
    last_query = None
    refresh_period_seconds = 10
    recent_failed_job_ids = LRUSet(1000)
    recent_successful_job_ids = LRUSet(1000)

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
                JobStatus.PENDING: now - datetime.timedelta(minutes=webapp_config.RUNNING_TIMEOUT),
            }
            cutoff.update({k.value: v for (k, v) in cutoff.items()})  # Add value to dict for backwards compat
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
            # Finally, check we have the latest updates with a small buffer
            _last_query = datetime.datetime.now() - datetime.timedelta(seconds=refresh_period_seconds)
            query_results = serializer.get_all_results(since=last_query)
            for result in query_results:
                ct += 1

                # Prometheus logging
                if result.status == JobStatus.DONE and result.job_id not in recent_successful_job_ids:
                    try_register_success_prometheus(result.report_name, result.report_title)
                    recent_successful_job_ids.add(result.job_id)
                if result.status == JobStatus.ERROR and result.job_id not in recent_failed_job_ids:
                    try_register_fail_prometheus(result.report_name, result.report_title)
                    recent_failed_job_ids.add(result.job_id)

                # Cache population
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
            logger.debug("Found {} updates since {}.".format(ct, last_query))
            last_query = _last_query
        except Exception as e:
            if run_once:
                raise
            logger.exception(str(e))
        if run_once:
            break
        time.sleep(refresh_period_seconds)
    logger.info("Report-hunting thread successfully killed.")
