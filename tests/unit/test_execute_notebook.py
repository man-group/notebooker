from __future__ import unicode_literals

from mock import patch
import pytest

from notebooker.execute_notebook import _get_overrides, docker_compose_entrypoint


@pytest.mark.parametrize(
    "json_overrides, iterate_override_values_of, expected_output",
    [
        ('{"test": [1, 2, 3]}', "", [{"test": [1, 2, 3]}]),
        ('{"test": [1, 2, 3]}', "test", [{"test": 1}, {"test": 2}, {"test": 3}]),
        ('{"test": [1, 2, 3], "a": 1}', "test", [{"test": 1, "a": 1}, {"test": 2, "a": 1}, {"test": 3, "a": 1}]),
        (
            '[{"test": 1, "a": 1}, {"test": 2, "a": 1}, {"test": 3, "a": 1}]',
            None,
            [{"test": 1, "a": 1}, {"test": 2, "a": 1}, {"test": 3, "a": 1}],
        ),
        ('[{"test": 1, "a": 1}]', None, [{"test": 1, "a": 1}]),
        ("[]", None, []),
    ],
)
def test_get_overrides(json_overrides, iterate_override_values_of, expected_output):
    actual_output = _get_overrides(json_overrides, iterate_override_values_of)
    assert isinstance(actual_output, list)
    for override in actual_output:
        assert override in expected_output


@pytest.mark.parametrize(
    "input_json, iterate_override_values_of, error_message",
    [
        (
            '{"test": {"Equities": "hello", "FX": "world"}, "a": 1}',
            "test",
            "Can't iterate over a non-list or tuple of variables. "
            "The given value was a <class 'dict'> - {'Equities': 'hello', 'FX': 'world'}.",
        ),
        (
            '{"test": {"Equities": "hello", "FX": "world"}, "a": 1}',
            "notfound",
            "Can't iterate over override values unless it is given in the override.*",
        ),
        ("{}", "test", "Can't iterate over override values unless it is given in the override.*"),
    ],
)
def test_get_overrides_valueerror(input_json, iterate_override_values_of, error_message):
    with pytest.raises(ValueError, match=error_message):
        _get_overrides(input_json, iterate_override_values_of)


def test_docker_compose_entrypoint_propagates_exit_code():
    with patch("notebooker.execute_notebook.sys.argv", ["", "--help"]):
        assert docker_compose_entrypoint() == 0
    with patch("notebooker.execute_notebook.sys.argv", ["", "--invalid-arg"]):
        assert docker_compose_entrypoint() != 0
