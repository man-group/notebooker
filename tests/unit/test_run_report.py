import subprocess
import sys

import mock

from notebooker.web.routes.run_report import _monitor_stderr


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

    with mock.patch("notebooker.web.routes.run_report.get_fresh_serializer") as serializer:
        stderr_output = _monitor_stderr(p, "abc123")
    assert stderr_output == expected_output

    serializer().update_stdout.assert_has_calls(
        [
            mock.call("abc123", new_lines=["This is going to stderr\n"]),
            mock.call("abc123", new_lines=["This is going to stderr a bit later\n"]),
        ]
    )
