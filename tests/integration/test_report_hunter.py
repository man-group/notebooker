import datetime
import uuid

import freezegun
import pytest

from notebooker.constants import JobStatus, NotebookResultComplete, NotebookResultError, NotebookResultPending
from notebooker.serialization.serialization import initialize_serializer_from_config
from notebooker.utils.caching import get_report_cache
from notebooker.utils.filesystem import initialise_base_dirs
from notebooker.web.report_hunter import _report_hunter


@pytest.fixture(autouse=True)
def clean_file_cache(clean_file_cache):
    """Set up cache encironment."""


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
        serializer.update_check_status(
            job_id,
            JobStatus.DONE,
            raw_html_resources={"outputs": {}},
            job_finish_time=datetime.datetime.now(),
            pdf="",
            raw_ipynb_json="[]",
            raw_html="",
            email_html="",
        )
        _report_hunter(webapp_config=webapp_config, run_once=True)

        expected = NotebookResultComplete(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.DONE,
            update_time=datetime.datetime(2018, 1, 12, 2, 37),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_finish_time=datetime.datetime(2018, 1, 12, 2, 37),
            raw_html="",
            email_html="",
            raw_html_resources={"outputs": {}},
            raw_ipynb_json="[]",
        )
        assert get_report_cache(report_name, job_id, cache_dir=webapp_config.CACHE_DIR) == expected
