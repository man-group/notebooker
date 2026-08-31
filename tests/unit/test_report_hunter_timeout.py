import datetime

import freezegun
import mock
import pytest

import notebooker.web.report_hunter as report_hunter
from notebooker.constants import JobStatus, NotebookResultPending
from notebooker.settings import WebappConfig

START_TIME = datetime.datetime(2018, 1, 12, 2, 30)


def _run_report_hunter(status, minutes_waited):
    """Drive the timeout branch of _report_hunter with a stub serializer, so no mongo is needed."""
    pending = NotebookResultPending(
        job_id="job-id",
        report_name="report-name",
        report_title="report-name",
        status=status,
        update_time=START_TIME,
        job_start_time=START_TIME,
    )
    captured = {}

    serializer = mock.MagicMock()
    serializer.get_all_results.side_effect = lambda *args, **kwargs: [pending]
    serializer.update_check_status.side_effect = lambda job_id, new_status, error_info=None, **kw: captured.update(
        status=new_status, error_info=error_info
    )

    # Nested rather than a parenthesized group, since setup.py declares python_requires>=3.6
    # and parenthesized context managers need 3.10.
    with mock.patch.object(report_hunter, "initialize_serializer_from_config", return_value=serializer):
        with mock.patch.object(report_hunter, "get_report_cache", return_value=None):
            with mock.patch.object(report_hunter, "set_report_cache"):
                with freezegun.freeze_time(START_TIME + datetime.timedelta(minutes=minutes_waited)):
                    report_hunter._report_hunter(webapp_config=WebappConfig(), run_once=True)

    return captured


@pytest.mark.parametrize(
    "status, minutes_waited",
    [
        (JobStatus.SUBMITTED, 4),
        (JobStatus.SUBMITTED, 60),
        (JobStatus.SUBMITTED, 1440),
        (JobStatus.PENDING, 61),
        (JobStatus.PENDING, 600),
    ],
)
def test_timeout_message_reports_real_elapsed_time(status, minutes_waited):
    """The message must reflect how long the job actually waited, not the timeout setting."""
    captured = _run_report_hunter(status, minutes_waited)

    assert captured["status"] == JobStatus.TIMEOUT
    assert "Timed out after {} minutes 0 seconds.".format(minutes_waited) in captured["error_info"]


@pytest.mark.parametrize(
    "status, expected_stage",
    [
        (JobStatus.SUBMITTED, "while being submitted to run"),
        (JobStatus.PENDING, "while running"),
    ],
)
def test_timeout_message_describes_the_right_stage(status, expected_stage):
    captured = _run_report_hunter(status, minutes_waited=1440)
    assert "This request timed out {}.".format(expected_stage) in captured["error_info"]
