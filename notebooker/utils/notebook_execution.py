import os
import re
import shutil
import tempfile
from logging import getLogger
from typing import AnyStr, Union

from notebooker.constants import TEMPLATE_DIR_SEPARATOR, NotebookResultComplete, NotebookResultError
from notebooker.utils.mail import mail

logger = getLogger(__name__)


def _output_dir(output_base_dir, report_name, job_id):
    return os.path.join(output_base_dir, report_name, job_id)


def send_result_email(result: Union[NotebookResultComplete, NotebookResultError]) -> None:
    from_email = "notebooker@notebooker.io"
    to_email = result.mailto
    report_title = (
        result.report_title.decode("utf-8") if isinstance(result.report_title, bytes) else result.report_title
    )
    subject = result.email_subject or f"Notebooker: {report_title} report completed with status: {result.status.value}"
    body = result.email_html or result.raw_html
    attachments = []
    tmp_dir = None
    try:
        if isinstance(result, NotebookResultComplete):
            tmp_dir = tempfile.mkdtemp(dir=os.path.expanduser("~"))
            # Attach PDF output to the email. Has to be saved to disk temporarily for the mail API to work.
            report_name = result.report_name.replace(os.sep, TEMPLATE_DIR_SEPARATOR)
            if isinstance(report_name, bytes):
                report_name = report_name.decode("utf-8")
            if result.pdf:
                pdf_name = "{}_{}.pdf".format(report_name, result.job_start_time.strftime("%Y-%m-%dT%H%M%S"))
                pdf_path = os.path.join(tmp_dir, pdf_name)
                with open(pdf_path, "wb") as f:
                    f.write(result.pdf)
                attachments.append(pdf_path)

            # Embed images into the email as attachments with "cid" links.
            for resource_path, resource in result.raw_html_resources.get("outputs", {}).items():
                resource_path_short = resource_path.rsplit(os.sep, 1)[1]
                new_path = os.path.join(tmp_dir, resource_path_short)
                with open(new_path, "wb") as f:
                    f.write(resource)

                body = re.sub(
                    r'<img src="{}"'.format(resource_path), r'<img src="cid:{}"'.format(resource_path_short), body
                )
                attachments.append(new_path)

        msg = ["Please either activate HTML emails, or see the PDF attachment.", body]

        logger.info("Sending email to %s with %d attachments", to_email, len(attachments))
        mail(from_email, to_email, subject, msg, attachments=attachments)
    finally:
        if tmp_dir:
            logger.info("Cleaning up temporary email attachment directory %s", tmp_dir)
            shutil.rmtree(tmp_dir)
