import datetime
import re
import sys

import pytest
from six import PY2

from notebooker.web.handle_overrides import handle_overrides

IMPORT_REGEX = re.compile("^(from [a-zA-Z0-9_.]+ )?import (?P<import_target>[a-zA-Z0-9_.]+)( as (?P<name>.+))?$")
VARIABLE_ASSIGNMENT_REGEX = re.compile("^(?P<variable_name>[a-zA-Z_]+) *= *(?P<value>.+)$")


@pytest.mark.parametrize(
    "test_name, input_str, expected_output_values, expected_issues",
    [
        (
            "Neither import nor variable declaration",
            "datetime.datetime(2018, 1, 1)",
            {},
            ["An error was encountered: name 'datetime' is not defined"],
        ),
        (
            "Using un-imported module",
            "d = datetime.datetime(2018, 1, 1)",
            {},
            ["An error was encountered: name 'datetime' is not defined"],
        ),
        (
            "Successfully importing and using a library",
            "import datetime\nd = datetime.datetime(2018, 1, 1)",
            {},
            [
                'Could not JSON serialise a parameter ("d") - this must be serialisable so that we can '
                "execute the notebook with it! (Error: {})".format(
                    "datetime.datetime(2018, 1, 1, 0, 0) is not JSON serializable, Value: 2018-01-01 00:00:00"
                    if PY2
                    else
                    "Object of type 'datetime' is not JSON serializable, Value: 2018-01-01 00:00:00"
                    if sys.version_info < (3, 7)
                    else "Object of type datetime is not JSON serializable, Value: 2018-01-01 00:00:00"
                )
            ],
        ),
        (
            "Successfully importing and using a library",
            "import datetime\nd = datetime.datetime(2018, 1, 1).isoformat()",
            {"d": "2018-01-01T00:00:00"},
            [],
        ),
        (
            "Successfully importing and using a library",
            "from datetime import datetime as dt;d = dt(2018, 1, 1).isoformat()\nq=\\\ndt(2011, 5, 1).isoformat()",
            {"d": datetime.datetime(2018, 1, 1).isoformat(), "q": datetime.datetime(2011, 5, 1).isoformat()},
            [],
        ),
        (
            "Failing importing and using an un-imported library",
            "import datetimes\nd = datetime.datetime(2018, 1, 1)",
            {},
            ["An error was encountered: No module named {}".format("datetimes" if PY2 else "'datetimes'")],
        ),
        (
            "Importing but just using an expression",
            "import datetime;datetime.datetime(2018, 1, 1)",
            {},
            ["Found an expression that did nothing! It has a value of type: <class '_ast.Call'>"],
        ),
    ],
)
def test_handle_overrides_normal(test_name, input_str, expected_output_values, expected_issues):
    issues = []
    override_dict = handle_overrides(input_str, issues)
    assert sorted(issues) == sorted(expected_issues)
    assert sorted(override_dict.items()) == sorted(expected_output_values.items())
