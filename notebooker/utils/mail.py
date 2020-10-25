import logging

# For guessing MIME type based on file name extension
import mimetypes
import os
import smtplib
from email import encoders, message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Tuple, Union

logger = logging.getLogger(__name__)

_SMTP_SERVER_ENV_KEY = "SMTP_SERVER"


def mail(from_address, to_address, subject, msg, attachments=None, server=""):
    """
    Sends a mail both with and without attachments.

    Arguments
    =========

    from_address:
        string holding sender's address
    to_address:
        string holding comma separated list of recipients
    subject:
        string containing subject
    msg:
        string containing email body message in plain text or a list
        with first entry the body message string as plain text and the
        second entry the body message string as html
    attachments (optional):
        list or a string holding comma separated list of (absolute
        or/and relative) paths to attachments
    server (optional):
        string holding SMTP server e.g. 'mailhost.domain.com'. Value will be
        picked from environment variable (SMTP_SERVER) or default to None (localhost) if no value is provided

    Examples
    ========

    # basic email to two recipients
    >> mail("sender_name@domain.com", "x@domain.com,y@domain.com", "TestSubject", "This is a test message")

    # email with attachments
    mail("sender_name@domain.com", "x@domain.com", "TestSubject", "This is a test message",
         "test1.pdf,test2.pdf,test.doc,/users/is/generic/myreport.csv"))
    """
    if isinstance(to_address, list):
        recipients = to_address
        to_address = ",".join(to_address)
    else:
        recipients = [el.strip() for el in to_address.split(",")]

    if isinstance(attachments, str):
        attachments = attachments.split(",")

    server = server or os.environ.get(_SMTP_SERVER_ENV_KEY, "localhost")
    logger.debug("Sending email using smtp server {}".format(server))
    s = smtplib.SMTP()
    s.connect(server)
    s.sendmail(from_address, recipients, _generate_mail_msg(from_address, to_address, subject, msg, attachments))
    s.close()


def _generate_mail_msg(from_address, to_address, subject, msg, attachments=None):
    msg_plain, msg_html = _separate_plain_and_html_parts(msg)
    contains_html = msg_html is not None
    has_attachments = attachments is not None
    message_root = _construct_message_root(has_attachments, contains_html)

    message_root["Subject"] = subject
    message_root["From"] = from_address
    message_root["To"] = to_address

    if not has_attachments and not contains_html:
        message_root.set_payload(msg_plain)
    elif has_attachments:
        message_root = _process_attachments(message_root, msg_plain, msg_html, contains_html, attachments)
    else:
        # Case no attachment but html
        message_root.attach(MIMEText(msg_plain, "plain"))
        message_root.attach(MIMEText(msg_html, "html", "utf-8"))

    return message_root.as_string()


def _construct_message_root(has_attachments: bool, contains_html: bool) -> message.Message:
    if has_attachments:
        return MIMEMultipart("related")
    elif contains_html:
        return MIMEMultipart("alternative")
    else:
        return message.Message()


def _separate_plain_and_html_parts(msg: Union[str, List, Tuple]) -> (str, str):
    msg_plain = msg
    msg_html = None
    if type(msg) is list or type(msg) is tuple:
        try:
            msg_plain = msg[0]
        except IndexError:
            raise RuntimeError("No message body provided!")
        try:
            msg_html = msg[1]
        except IndexError:
            pass
    return msg_plain, msg_html


def _read_attachment(ctype: str, path: str) -> MIMEBase:
    maintype, subtype = ctype.split("/", 1)
    if maintype == "text":
        fp = open(path)
        # Note: we should handle calculating the charset
        msg_att = MIMEText(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "image":
        fp = open(path, "rb")
        msg_att = MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "audio":
        fp = open(path, "rb")
        msg_att = MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    else:
        fp = open(path, "rb")
        msg_att = MIMEBase(maintype, _subtype=subtype)
        msg_att.set_payload(fp.read())
        fp.close()
        # Encode the payload using Base64
        encoders.encode_base64(msg_att)
    return msg_att


def _process_attachments(message_root, msg_plain, msg_html, contains_html, attachments):
    message_root.preamble = "This is a multi-part message in MIME format."
    message_root.attach(_construct_alternative_message_part(msg_plain, msg_html, contains_html))

    for path in attachments:
        if not os.path.isfile(path):
            logger.info("Attachment '%s' doesn't appear to be a file => Will ignore it" % path)
            continue
        message_root.attach(_process_one_attachment(path))
    return message_root


def _process_one_attachment(path):
    """
    Guess the content type based on the file's extension.  Encoding
    will be ignored, although we should check for simple things like
    gzip'd or compressed files.
    """
    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = "application/octet-stream"

    msg_att = _read_attachment(ctype, path)
    msg_att.add_header("Content-Disposition", "attachment", filename=os.path.basename(path))
    return msg_att


def _construct_alternative_message_part(msg_plain, msg_html, contains_html):
    """
    Encapsulate the plain and HTML versions of the message body in an
    'alternative' part, so message agents can decide which they want to display.
    """
    msgAlternative = MIMEMultipart("alternative")

    msgText = MIMEText(msg_plain, "plain")
    msgAlternative.attach(msgText)

    if contains_html:
        htmlText = MIMEText(msg_html, "html", "utf-8")
        msgAlternative.attach(htmlText)

    return msgAlternative
