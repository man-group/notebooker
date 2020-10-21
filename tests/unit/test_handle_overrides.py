from __future__ import unicode_literals

import datetime
import re
import sys
from typing import Any

import freezegun
import hypothesis
import hypothesis.strategies as st
import mock
import pytest
from six import PY2, PY3

from notebooker.web.handle_overrides import _handle_overrides_safe, handle_overrides

IMPORT_REGEX = re.compile(r"^(from [a-zA-Z0-9_.]+ )?import (?P<import_target>[a-zA-Z0-9_.]+)( as (?P<name>.+))?$")
VARIABLE_ASSIGNMENT_REGEX = re.compile(r"^(?P<variable_name>[a-zA-Z_]+) *= *(?P<value>.+)$")


@hypothesis.given(st.text())
def test_handle_overrides_handles_anything_cleanly_no_process_junk(text):
    # Check that it doesn't just crash with random input
    with mock.patch("notebooker.web.handle_overrides.subprocess.check_output") as popen:
        popen.side_effect = lambda args: mock.MagicMock(res=_handle_overrides_safe(args[4], args[6]))
        handle_overrides(text, issues=[])


@hypothesis.given(st.from_regex(VARIABLE_ASSIGNMENT_REGEX))
def test_handle_overrides_handles_anything_cleanly_no_process_variable(text):
    with mock.patch("notebooker.web.handle_overrides.subprocess.check_output") as popen:
        popen.side_effect = lambda args: mock.MagicMock(res=_handle_overrides_safe(args[4], args[6]))
        issues = []
        overrides = handle_overrides(text, issues)
    if any(t for t in text.split("\n") if t.strip()):
        assert len(issues) >= 1 or len(overrides) >= 1
    else:
        assert len(issues) == 0 and len(overrides) == 0


_CACHE = {}


def _fakepickle_dump(to_pickle, file):
    # type: (Any, file) -> None
    global _CACHE
    _CACHE[file.name] = to_pickle


def _fakepickle_load(file):
    # type: (file) -> Any
    global _CACHE
    return _CACHE[file.name]


@hypothesis.given(st.from_regex(IMPORT_REGEX))
@hypothesis.settings(max_examples=30)
def test_handle_overrides_handles_anything_cleanly_no_process_import(text):
    with mock.patch("notebooker.web.handle_overrides.subprocess.check_output") as popen:
        with mock.patch("notebooker.web.handle_overrides.pickle") as pickle:
            pickle.dump.side_effect = _fakepickle_dump
            pickle.load.side_effect = _fakepickle_load
            popen.side_effect = lambda args: mock.MagicMock(res=_handle_overrides_safe(args[4], args[6]))
            issues = []
            overrides = handle_overrides(text, issues)
    if any(t for t in text.split("\n") if t.strip()):
        assert len(issues) >= 1 or len(overrides) >= 1
    else:
        assert len(issues) == 0 and len(overrides) == 0


@freezegun.freeze_time(datetime.datetime(2018, 1, 1))
@pytest.mark.parametrize(
    "input_txt",
    [
        "import datetime;d=datetime.datetime.now().isoformat()",
        "import datetime as dt;d=dt.datetime.now().isoformat()",
        "from datetime import datetime;d=datetime.now().isoformat()",
        "from datetime import datetime as dt;d=dt.now().isoformat()",
    ],
)
def test_handle_overrides_handles_imports(input_txt):
    with mock.patch("notebooker.web.handle_overrides.subprocess.check_output") as popen:
        popen.side_effect = lambda args: mock.MagicMock(res=_handle_overrides_safe(args[4], args[6]))
        issues = []
        overrides = handle_overrides(input_txt, issues)
    assert overrides == {"d": datetime.datetime(2018, 1, 1).isoformat()}


@pytest.mark.parametrize("input_txt", ["import datetime;d=datetime.datetime(10, 1, 1)"])
def test_handle_overrides_handles_imports_with_issues(input_txt):
    with mock.patch("notebooker.web.handle_overrides.subprocess.check_output") as popen:
        popen.side_effect = lambda args: mock.MagicMock(res=_handle_overrides_safe(args[4], args[6]))
        issues = []
        overrides = handle_overrides(input_txt, issues)
    assert overrides == {}
    if PY2:
        error_string = "datetime.datetime(10, 1, 1, 0, 0) is not JSON serializable, Value: 0010-01-01 00:00:00"
    elif sys.version_info < (3, 7):
        error_string = "Object of type 'datetime' is not JSON serializable, Value: 0010-01-01 00:00:00"
    else:
        error_string = "Object of type datetime is not JSON serializable, Value: 0010-01-01 00:00:00"
    assert issues == [
        'Could not JSON serialise a parameter ("d") - '
        "this must be serialisable so that we can execute "
        "the notebook with it! "
        "(Error: {})".format(error_string)
    ]
