# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from notebooker import constants
from notebooker.utils import web
from notebooker.utils.web import json_to_python


@pytest.mark.parametrize(
    "test_name, mailto, expected_issues, expected_mailto",
    [
        ("simple email", "hello@test-email.com", [], "hello@test-email.com"),
        ("simple email, trailing spaces", "hello@test-email.com   \n", [], "hello@test-email.com"),
        ("space in email", "hello @test-email.com", [constants.EMAIL_SPACE_ERR_MSG], "hello @test-email.com"),
        ("apostrophe", "o'neill@test-email.com", [], "o'neill@test-email.com"),
        ("weird email address", "å∂ßåß∂@test-email.com", [], "å∂ßåß∂@test-email.com"),
        (
            "forbidden char",
            'o"neill@test-email.com',
            ["This report has an invalid input (o\"neill@test-email.com) - it must not contain any of ['\"']."],
            'o"neill@test-email.com',
        ),
    ],
)
def test_validate_mailto(test_name, mailto, expected_issues, expected_mailto):
    issues = []
    actual_mailto = web.validate_mailto(mailto, issues)
    assert issues == expected_issues
    assert actual_mailto == expected_mailto


@pytest.mark.parametrize(
    "test_name, title, expected_issues, expected_mailto",
    [
        ("simple title", "adasdasda", [], "adasdasda"),
        ("title with emojis", "😀 😁 😂", [], "😀 😁 😂"),
        ("apostrophe", "''''''''''''''", [], "''''''''''''''"),
        (
            "forbidden char",
            'this is "great"',
            ['This report has an invalid input (this is "great") - it must not contain any of [\'"\'].'],
            'this is "great"',
        ),
    ],
)
def test_validate_title(test_name, title, expected_issues, expected_mailto):
    issues = []
    actual_title = web.validate_title(title, issues)
    assert issues == expected_issues
    assert actual_title == expected_mailto


@pytest.mark.parametrize(
    "input_json,output_python",
    [
        (None, None),
        ("", None),
        ('{"test": "me"}', "test = 'me'"),
        ('{"test": [2, 3, 4]}', "test = [2, 3, 4]"),
        ('{"test": false}', "test = False"),
        ('{"test": 23}', "test = 23"),
        ('{"test": 2.3}', "test = 2.3"),
        (
            '{"test": "me", "hello": "world", "blah": 5}',
            """blah = 5
hello = 'world'
test = 'me'""",
        ),
        (
            '{"test": "me", "hello": true, "blah": 5}',
            """blah = 5
hello = True
test = 'me'""",
        ),
    ],
)
def test_json_to_python(input_json, output_python):
    if output_python is None:
        assert json_to_python(input_json) is None
    else:
        assert json_to_python(input_json) == output_python
