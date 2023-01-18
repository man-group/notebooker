import subprocess
import sys

import mock
from werkzeug.datastructures import CombinedMultiDict, ImmutableMultiDict

from notebooker.constants import DEFAULT_SERIALIZER
from notebooker.web.routes.run_report import _monitor_stderr, validate_run_params, RunReportParams


def test_monitor_stderr():
    dummy_process = """
import time, sys
sys.stdout.write(u'This is going to stdout\\n')
sys.stderr.write(u'This is going to stderr\\n')
time.sleep(1)
sys.stdout.write(u'This is going to stdout a bit later\\n')
sys.stderr.write(u'This is going to stderr a bit later\\n')
"""
    expected_output = """This is going to stderr
This is going to stderr a bit later
"""
    p = subprocess.Popen([sys.executable, "-c", dummy_process], stderr=subprocess.PIPE)

    with mock.patch("notebooker.web.routes.run_report.get_serializer_from_cls") as serializer:
        stderr_output = _monitor_stderr(p, "abc123", DEFAULT_SERIALIZER, {})
    assert stderr_output == expected_output

    serializer().update_stdout.assert_has_calls(
        [
            mock.call("abc123", new_lines=["This is going to stderr\n"]),
            mock.call("abc123", new_lines=["This is going to stderr a bit later\n"]),
            mock.call("abc123", ["This is going to stderr\n", "This is going to stderr a bit later\n"], replace=True),
        ]
    )


def test_validate_run_params():
    input_params = CombinedMultiDict(
        [
            ImmutableMultiDict(
                [
                    ("overrides", "{}"),
                    ("report_title", "asdas"),
                    ("mailto", ""),
                    ("generate_pdf", "True"),
                    ("hide_code", "True"),
                    ("scheduler_job_id", "plot_random_asdas"),
                    ("mailfrom", "test@example.com"),
                    ("is_slideshow", "on"),
                ]
            ),
            ImmutableMultiDict([]),
        ]
    )
    issues = []
    expected_output = RunReportParams(
        report_title="asdas",
        mailto="",
        generate_pdf_output=True,
        hide_code=True,
        scheduler_job_id="plot_random_asdas",
        mailfrom="test@example.com",
        is_slideshow=True,
    )
    actual_output = validate_run_params(input_params, issues)
    assert issues == []
    assert actual_output == expected_output
