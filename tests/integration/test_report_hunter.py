import datetime
import uuid

import freezegun
import mock.mock
import pytest

from notebooker.constants import JobStatus, NotebookResultComplete, NotebookResultError, NotebookResultPending
from notebooker.serialization.serialization import initialize_serializer_from_config
from notebooker.utils.caching import get_report_cache
from notebooker.utils.filesystem import initialise_base_dirs
from notebooker.utils.results import _get_job_results
from notebooker.web.report_hunter import _report_hunter, LRUSet


@pytest.fixture(autouse=True)
def clean_file_cache(clean_file_cache):
    """Set up cache environment."""


def test_report_hunter_with_nothing(bson_library, webapp_config):
    _report_hunter(webapp_config=webapp_config, run_once=True)


@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_report_hunter_with_one(bson_library, webapp_config):
    serializer = initialize_serializer_from_config(webapp_config)

    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer.save_check_stub(job_id, report_name)
    _report_hunter(webapp_config=webapp_config, run_once=True)
    expected = NotebookResultPending(
        job_id=job_id,
        report_name=report_name,
        report_title=report_name,
        update_time=datetime.datetime(2018, 1, 12),
        job_start_time=datetime.datetime(2018, 1, 12),
    )
    assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected


def test_report_hunter_with_status_change(bson_library, webapp_config):
    initialise_base_dirs(webapp_config=webapp_config)
    serializer = initialize_serializer_from_config(webapp_config)

    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 30)):
        serializer.save_check_stub(job_id, report_name)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        expected = NotebookResultPending(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            update_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 32)):
        serializer.update_check_status(job_id, JobStatus.CANCELLED, error_info="This was cancelled!")
        _report_hunter(webapp_config=webapp_config, run_once=True)

        expected = NotebookResultError(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.CANCELLED,
            update_time=datetime.datetime(2018, 1, 12, 2, 32),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            error_info="This was cancelled!",
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected


@pytest.mark.parametrize(
    "status, time_later, should_timeout",
    [
        (JobStatus.SUBMITTED, datetime.timedelta(minutes=1), False),
        (JobStatus.SUBMITTED, datetime.timedelta(minutes=4), True),
        (JobStatus.PENDING, datetime.timedelta(minutes=4), False),
        (JobStatus.PENDING, datetime.timedelta(minutes=61), True),
    ],
)
def test_report_hunter_timeout(bson_library, status, time_later, should_timeout, webapp_config):
    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())

    serializer = initialize_serializer_from_config(webapp_config)
    start_time = time_now = datetime.datetime(2018, 1, 12, 2, 30)
    with freezegun.freeze_time(time_now):
        serializer.save_check_stub(job_id, report_name, status=status)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        expected = NotebookResultPending(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=status,
            update_time=time_now,
            job_start_time=start_time,
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected

    time_now += time_later
    with freezegun.freeze_time(time_now):
        _report_hunter(webapp_config=webapp_config, run_once=True)

        if should_timeout:
            mins = (time_later.total_seconds() / 60) - 1
            expected = NotebookResultError(
                job_id=job_id,
                report_name=report_name,
                report_title=report_name,
                status=JobStatus.TIMEOUT,
                update_time=time_now,
                job_start_time=start_time,
                error_info="This request timed out while being submitted to run. "
                "Please try again! "
                "Timed out after {:.0f} minutes 0 seconds.".format(mins),
            )
        else:
            # expected does not change
            pass
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected


@mock.patch("notebooker.web.routes.prometheus.record_failed_report")
def test_prometheus_logging_when_cache_is_already_updated(record_failed_report, bson_library, webapp_config):
    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer = initialize_serializer_from_config(webapp_config)

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 30)):
        serializer.save_check_stub(job_id, report_name, status=JobStatus.SUBMITTED)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        expected = NotebookResultPending(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.SUBMITTED,
            update_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 5, 37)):
        expected = NotebookResultError(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.ERROR,
            update_time=datetime.datetime(2018, 1, 12, 5, 37),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            error_info="This crashed!",
        )
        serializer.save_check_result(expected)

        # Now someone checks the result on the webapp, which updates the cache...!
        _get_job_results(job_id, report_name, serializer=serializer, ignore_cache=True)

        _report_hunter(webapp_config=webapp_config, run_once=True)
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected
        record_failed_report.assert_called_once_with(report_name, report_name)


def test_report_hunter_pending_to_done(bson_library, webapp_config):
    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer = initialize_serializer_from_config(webapp_config)

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 30)):
        serializer.save_check_stub(job_id, report_name, status=JobStatus.SUBMITTED)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        expected = NotebookResultPending(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.SUBMITTED,
            update_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 32)):
        serializer.update_check_status(job_id, JobStatus.PENDING)
        _report_hunter(webapp_config=webapp_config, run_once=True)

        expected = NotebookResultPending(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.PENDING,
            update_time=datetime.datetime(2018, 1, 12, 2, 32),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 37)):
        expected = NotebookResultComplete(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.DONE,
            update_time=datetime.datetime(2018, 1, 12, 2, 37),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_finish_time=datetime.datetime(2018, 1, 12, 2, 37),
            pdf=b"abc",
            raw_html="rawstuff",
            email_html="emailstuff",
            raw_html_resources={"outputs": {}, "inlining": []},
            raw_ipynb_json="[]",
        )
        serializer.save_check_result(expected)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected


@mock.patch("notebooker.web.routes.prometheus.record_failed_report")
def test_prometheus_logging_in_report_hunter_no_prometheus_fail(record_failed_report, bson_library, webapp_config):
    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer = initialize_serializer_from_config(webapp_config)
    record_failed_report.side_effect = ImportError("wah")

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 37)):
        expected = NotebookResultError(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.ERROR,
            update_time=datetime.datetime(2018, 1, 12, 2, 37),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            error_info="This was cancelled!",
        )
        serializer.save_check_result(expected)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected
        record_failed_report.assert_called_once_with(report_name, report_name)


@mock.patch("notebooker.web.routes.prometheus.record_successful_report")
def test_prometheus_logging_in_report_hunter_no_prometheus_success(
    record_successful_report, bson_library, webapp_config
):
    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer = initialize_serializer_from_config(webapp_config)
    record_successful_report.side_effect = ImportError("wah")

    with freezegun.freeze_time(datetime.datetime(2018, 1, 12, 2, 37)):
        expected = NotebookResultComplete(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.DONE,
            update_time=datetime.datetime(2018, 1, 12, 2, 37),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_finish_time=datetime.datetime(2018, 1, 12, 2, 37),
            pdf=b"abc",
            raw_html="rawstuff",
            email_html="emailstuff",
            raw_html_resources={"outputs": {}, "inlining": []},
            raw_ipynb_json="[]",
        )
        serializer.save_check_result(expected)
        _report_hunter(webapp_config=webapp_config, run_once=True)
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected
        record_successful_report.assert_called_once_with(report_name, report_name)


def test_lru_set():
    s = LRUSet(max_size=10)
    assert len(s) == 0
    for i in range(100):
        s.add(i)
    assert len(s) == 10
    for i in range(90):
        assert i not in s
    for i in range(90, 100):
        assert i in s
    s.remove(99)
    assert 99 not in s
    assert len(s) == 9
    for set_item, range_item in zip(s, range(90, 99)):
        assert set_item == range_item
