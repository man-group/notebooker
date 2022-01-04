# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

import mock
import pytest

from notebooker.constants import NotebookResultComplete
from notebooker.utils import notebook_execution


@pytest.mark.parametrize(
    "test_name, job_id, report_name, report_title, expected_title",
    [
        (
            "unicode_overload",
            "aåß∂å∂",
            "®eπºr† ñaµé",
            "😒 😓 😔 ",
            "Notebooker: 😒 😓 😔  report completed with status: Checks done!",
        ),
        (
            "ascii only, encoded",
            "my job id",
            "my report name",
            "my report title",
            "Notebooker: my report title report completed with status: Checks done!",
        ),
    ],
)
def test_send_result_email(test_name, job_id, report_name, report_title, expected_title):
    to_email = "∫åññîsté®@test-email.com"
    mailfrom = "test@example.com"
    body_in = "<body><h1>hello  😆 😉 😊 😋 😎</h1></body>"
    result = NotebookResultComplete(
        job_id=job_id,
        job_start_time=datetime.datetime.now(),
        job_finish_time=datetime.datetime.now(),
        raw_html_resources={},
        raw_ipynb_json={},
        raw_html=body_in,
        email_html=body_in,
        mailto=to_email,
        pdf="",
        report_name=report_name,
        report_title=report_title,
        mailfrom=mailfrom,
    )
    with mock.patch("notebooker.utils.notebook_execution.mail") as mail:
        notebook_execution.send_result_email(result, "notebooker@localhost")
    email_sent = mail.mock_calls[0][1]
    assert len(email_sent) == 4, "mail() was not called with the correct number of args"
    from_address = email_sent[0]
    to_address = email_sent[1]
    title = email_sent[2]
    body = email_sent[3]

    assert from_address == mailfrom
    assert to_address == to_email
    assert title == expected_title
    assert body == ["Please either activate HTML emails, or see the PDF attachment.", body_in]


def test_send_result_email_fallback_to_raw_html():
    body_in = "<body><h1>hello  😆 😉 😊 😋 😎</h1></body>"
    to_email = "hello@you"
    result = NotebookResultComplete(
        job_id="fallback",
        job_start_time=datetime.datetime.now(),
        job_finish_time=datetime.datetime.now(),
        mailto=to_email,
        raw_html_resources={},
        raw_ipynb_json={},
        raw_html=body_in,
        pdf="",
        report_name="fallback",
        report_title="fallback",
    )
    with mock.patch("notebooker.utils.notebook_execution.mail") as mail:
        notebook_execution.send_result_email(result, "notebooker@localhost")
    email_sent = mail.mock_calls[0][1]
    assert len(email_sent) == 4, "mail() was not called with the correct number of args"
    from_address = email_sent[0]
    to_address = email_sent[1]
    title = email_sent[2]
    body = email_sent[3]

    assert from_address == "notebooker@localhost"
    assert to_address == to_email
    assert title == "Notebooker: fallback report completed with status: Checks done!"
    assert body == ["Please either activate HTML emails, or see the PDF attachment.", body_in]


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("", "Notebooker: subjecttest report completed with status: Checks done!"),
        (None, "Notebooker: subjecttest report completed with status: Checks done!"),
        ("my super cool report title", "my super cool report title"),
    ]
)
def test_send_result_email_subject(subject, expected):
    body_in = "<body><h1>hello  😆 😉 😊 😋 😎</h1></body>"
    to_email = "∫åññîsté®@ahl.com"
    mailfrom = "test@example.com"
    result = NotebookResultComplete(
        job_id="subjecttest",
        job_start_time=datetime.datetime.now(),
        job_finish_time=datetime.datetime.now(),
        raw_html_resources={},
        raw_ipynb_json={},
        raw_html=body_in,
        mailto=to_email,
        email_subject=subject,
        pdf="",
        report_name="subjecttest",
        report_title="subjecttest",
        mailfrom=mailfrom,
    )
    with mock.patch("notebooker.utils.notebook_execution.mail") as mail:
        notebook_execution.send_result_email(result, "notebooker@localhost")
    email_sent = mail.mock_calls[0][1]
    assert len(email_sent) == 4, "mail() was not called with the correct number of args"
    from_address = email_sent[0]
    to_address = email_sent[1]
    title = email_sent[2]
    body = email_sent[3]

    assert from_address == mailfrom
    assert to_address == to_email
    assert title == expected
    assert body == ["Please either activate HTML emails, or see the PDF attachment.", body_in]
