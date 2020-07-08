import re

import pytest
from six import PY3

from notebooker.utils.mail import (
    _SMTP_SERVER_ENV_KEY,
    _construct_alternative_message_part,
    _construct_message_root,
    _generate_mail_msg,
    _process_attachments,
    _process_one_attachment,
    _read_attachment,
    _separate_plain_and_html_parts,
    mail,
)

try:
    from unittest.mock import Mock, patch, sentinel, call
except ImportError:
    from mock import Mock, patch, sentinel, call


_MAIL_MODULE = "notebooker.utils.mail."


def test_plain_msg():
    """Plain mail msg generated properly"""
    expected = (
        """Subject: this is the test subject\nFrom: sender@test.com\nTo: x@test-email.com\n\nthis is \n the body"""
    )
    assert expected == _generate_mail_msg(
        "sender@test.com", "x@test-email.com", "this is the test subject", "this is \n the body"
    )


def test_plain_msg_several_recipients():
    """Plain mail msg with several recipients generated properly"""
    expected = (
        "Subject: this is the test subject\nFrom: sender@test.com\n"
        "To: x@test-email.com,y@test-email.com\n\nthis is \n the body"
    )
    assert expected == _generate_mail_msg(
        "sender@test.com", "x@test-email.com,y@test-email.com", "this is the test subject", "this is \n the body"
    )


def test_html_msg():
    """Html message generated correctly"""

    expected = r"""Content-Type: multipart/alternative;\n?\s*boundary="===============(\d)+=="
MIME-Version: 1.0
Subject: this is the test html subject
From: sender@test.com
To: x@test-email.com, y@test-email.com

--===============(\d)+==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

this is 
 the plain body
--===============(\d)+==
Content-Type: text/html; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

PGh0bWw\+aHRtbCB0ZXN0PC9odG1sPg==

--===============(\d)+==--"""

    msg = _generate_mail_msg(
        "sender@test.com",
        "x@test-email.com, y@test-email.com",
        "this is the test html subject",
        ["this is \n the plain body", "<html>html test</html>"],
        None,
    )
    assert re.match(expected, msg)


@pytest.mark.parametrize(("server_arg", "expect_env_smtp"), [("arg_smtp", False), (None, True)])
def test_mail(server_arg, expect_env_smtp):
    s = Mock()
    with patch("smtplib.SMTP", return_value=s) as SMTP:
        with patch.dict("os.environ", {_SMTP_SERVER_ENV_KEY: "env_smtp"}):
            mail("from_add", "jbloggs@test-email.com", "subject", "msg", server=server_arg)

    expected_msg = "Subject: subject\nFrom: from_add\nTo: jbloggs@test-email.com\n\nmsg"

    assert SMTP.call_args_list == [call()]
    assert s.connect.call_args_list == [call("env_smtp" if expect_env_smtp else server_arg)]
    assert s.sendmail.call_args_list == [call("from_add", ["jbloggs@test-email.com"], expected_msg)]


@pytest.mark.parametrize(
    ("attachments", "html", "ctor", "args"),
    [
        (False, False, "message.Message", tuple()),
        (False, True, "MIMEMultipart", ("alternative",)),
        (True, False, "MIMEMultipart", ("related",)),
        (True, True, "MIMEMultipart", ("related",)),
    ],
)
def test_construct_message_root(attachments, html, ctor, args):
    with patch(_MAIL_MODULE + ctor) as mock_ctor:
        _construct_message_root(attachments, html)
        mock_ctor.assert_called_once_with(*args)


@pytest.mark.parametrize(
    ("msg", "parts"),
    [
        ("plain", ("plain", None)),
        (["plain"], ("plain", None)),
        (("plain",), ("plain", None)),
        (("plain", "html"), ("plain", "html")),
        (["plain", "html"], ("plain", "html")),
    ],
)
def test_separate_plain_and_html_parts(msg, parts):
    assert parts == _separate_plain_and_html_parts(msg)


@pytest.mark.parametrize(("bad_input",), [([],), (tuple(),)])
def test_separate_plain_and_html_parts_bad_cases(bad_input):
    with pytest.raises(RuntimeError):
        _separate_plain_and_html_parts(bad_input)


@pytest.mark.parametrize(
    ("ctype", "ctor", "arg"),
    [
        ("text/subtype", "MIMEText", None),
        ("image/subtype", "MIMEImage", None),
        ("audio/subtype", "MIMEAudio", None),
        ("blah/subtype", "MIMEBase", "blah"),
    ],
)
def test_read_attachment(ctype, ctor, arg):
    compat_builtin = "builtins.open" if PY3 else "__builtin__.open"
    with patch(_MAIL_MODULE + ctor) as mock_ctor:
        with patch(compat_builtin) as mo, patch(_MAIL_MODULE + "encoders"):
            _read_attachment(ctype, sentinel.path)
            arg = arg or mo.return_value.read.return_value
            mock_ctor.assert_called_once_with(arg, _subtype="subtype")


def test_process_attachments():
    message_root = Mock()
    msg_plain = Mock()
    msg_html = Mock()
    contains_html = Mock()
    attachments = ["not a file", "file"]
    with patch(_MAIL_MODULE + _construct_alternative_message_part.__name__) as camp:
        with patch(_MAIL_MODULE + _process_one_attachment.__name__) as poa:
            with patch("os.path.isfile") as is_file:
                is_file.side_effect = [False, True]
                _process_attachments(message_root, msg_plain, msg_html, contains_html, attachments)
    camp.assert_called_once_with(msg_plain, msg_html, contains_html)
    poa.assert_called_once_with("file")


@pytest.mark.parametrize(
    ("path", "guess_type", "call_args"),
    [
        ("p1", (None, "encoding1"), ("application/octet-stream", "p1")),
        ("p2", ("ctype2", "encoding2"), ("application/octet-stream", "p2")),
        ("p3", ("ctype3", None), ("ctype3", "p3")),
    ],
)
def test_process_one_attachment(path, guess_type, call_args):
    with patch(_MAIL_MODULE + _read_attachment.__name__) as ra:
        with patch("mimetypes.guess_type") as gt:
            gt.return_value = guess_type
            _process_one_attachment(path)
    gt.assert_called_once_with(path)
    ra.assert_called_once_with(*call_args)


def test_construct_alternative_message_part():
    expected = r"""Content-Type: multipart/alternative;\n?\s*boundary="===============(\d)+=="
MIME-Version: 1.0

--===============(\d)+==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

this is 
 the plain body
--===============(\d)+==
Content-Type: text/html; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

PGh0bWw\+aHRtbCB0ZXN0PC9odG1sPg==

--===============(\d)+==--"""

    message = _construct_alternative_message_part("this is \n the plain body", "<html>html test</html>", True)
    assert re.match(expected, message.as_string())
