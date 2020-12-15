import datetime
import logging
import os
from enum import Enum, unique
from typing import AnyStr, Optional

import attr

SUBMISSION_TIMEOUT = 3
RUNNING_TIMEOUT = 60
CANCEL_MESSAGE = "The webapp shut down while this job was running. Please resubmit with the same parameters."
TEMPLATE_DIR_SEPARATOR = "^"
DEFAULT_SERIALIZER = "PyMongoResultSerializer"
logger = logging.getLogger(__name__)


DEFAULT_DATABASE_NAME = "notebooker"
DEFAULT_MONGO_HOST = "localhost"
DEFAULT_RESULT_COLLECTION_NAME = "NOTEBOOK_OUTPUT"


def kernel_spec():
    return {
        "display_name": os.getenv("NOTEBOOK_KERNEL_NAME", "notebooker_kernel"),
        "language": "python",
        "name": os.getenv("NOTEBOOK_KERNEL_NAME", "notebooker_kernel"),
    }


def python_template_dir(py_template_base_dir, py_template_subdir) -> Optional[str]:
    if py_template_base_dir:
        return os.path.join(py_template_base_dir, py_template_subdir or "")
    return None


@unique
class JobStatus(Enum):
    DONE = "Checks done!"
    ERROR = "Error"
    CANCELLED = "CANCELLED"
    PENDING = "Running..."
    SUBMITTED = "Submitted to run"
    TIMEOUT = "Report timed out. Please try again!"
    DELETED = "This report has been deleted."

    @staticmethod
    def from_string(s: AnyStr) -> Optional["JobStatus"]:
        mapping = {
            x.value: x
            for x in (
                JobStatus.DONE,
                JobStatus.ERROR,
                JobStatus.CANCELLED,
                JobStatus.PENDING,
                JobStatus.SUBMITTED,
                JobStatus.TIMEOUT,
                JobStatus.DELETED,
            )
        }.get(s)
        return mapping


# Variables for inputs from web
EMAIL_SPACE_ERR_MSG = "The email address specified had whitespace! Please fix this before resubmitting."
FORBIDDEN_INPUT_CHARS = list('"')
FORBIDDEN_CHAR_ERR_MSG = "This report has an invalid input ({}) - it must not contain any of {}."


@attr.s()
class NotebookResultBase(object):
    job_id = attr.ib()
    job_start_time = attr.ib()
    report_name = attr.ib()
    status = attr.ib(default=JobStatus.ERROR)
    overrides = attr.ib(default=attr.Factory(dict))
    mailto = attr.ib(default="")
    generate_pdf_output = attr.ib(default=True)
    hide_code = attr.ib(default=False)
    stdout = attr.ib(default=attr.Factory(list))

    def saveable_output(self):
        out = attr.asdict(self)
        out["status"] = self.status.value
        return out


@attr.s()
class NotebookResultPending(NotebookResultBase):
    status = attr.ib(default=JobStatus.PENDING)
    update_time = attr.ib(default=datetime.datetime.now())
    report_title = attr.ib(default="")
    overrides = attr.ib(default=attr.Factory(dict))
    mailto = attr.ib(default="")
    generate_pdf_output = attr.ib(default=True)
    hide_code = attr.ib(default=False)


@attr.s()
class NotebookResultError(NotebookResultBase):
    status = attr.ib(default=JobStatus.ERROR)
    error_info = attr.ib(default="")
    update_time = attr.ib(default=datetime.datetime.now())
    report_title = attr.ib(default="")
    overrides = attr.ib(default=attr.Factory(dict))
    mailto = attr.ib(default="")
    generate_pdf_output = attr.ib(default=True)
    hide_code = attr.ib(default=False)

    @property
    def email_subject(self):
        return ""

    @property
    def raw_html(self):
        return """<p>This job resulted in an error: <br/><code style="white-space: pre-wrap;">{}</code></p>""".format(
            self.error_info
        )

    @property
    def email_html(self):
        return self.raw_html


@attr.s(repr=False)
class NotebookResultComplete(NotebookResultBase):
    job_start_time = attr.ib()
    job_finish_time = attr.ib()
    raw_html_resources = attr.ib(attr.Factory(dict))
    status = attr.ib(default=JobStatus.DONE)
    raw_ipynb_json = attr.ib(default="")
    raw_html = attr.ib(default="")
    email_html = attr.ib(default="")
    update_time = attr.ib(default=datetime.datetime.now())
    pdf = attr.ib(default="")
    report_title = attr.ib(default="")
    overrides = attr.ib(default=attr.Factory(dict))
    mailto = attr.ib(default="")
    email_subject = attr.ib(default="")
    generate_pdf_output = attr.ib(default=True)
    hide_code = attr.ib(default=False)
    stdout = attr.ib(default=attr.Factory(list))

    def html_resources(self):
        """ We have to save the raw images using Mongo GridFS - figure out where they will go here """
        resources = {}
        for k, v in self.raw_html_resources.items():
            if k == "outputs":
                resources[k] = list(v)
            else:
                resources[k] = v
        return resources

    def saveable_output(self):
        return {
            "raw_ipynb_json": self.raw_ipynb_json,
            "status": self.status.value,
            "report_name": self.report_name,
            "report_title": self.report_title,
            "raw_html": self.raw_html,
            "email_html": self.email_html,
            "raw_html_resources": self.html_resources(),
            "job_id": self.job_id,
            "job_start_time": self.job_start_time,
            "job_finish_time": self.job_finish_time,
            "mailto": self.mailto,
            "email_subject": self.email_subject,
            "overrides": self.overrides,
            "generate_pdf_output": self.generate_pdf_output,
            "hide_code": self.hide_code,
            "update_time": self.update_time,
        }

    def __repr__(self):
        return (
            "NotebookResultComplete(job_id={job_id}, status={status}, report_name={report_name}, "
            "job_start_time={job_start_time}, job_finish_time={job_finish_time}, update_time={update_time}, "
            "report_title={report_title}, overrides={overrides}, mailto={mailto}, "
            "email_subject={email_subject}, generate_pdf_output={generate_pdf_output}, hide_code={hide_code})".format(
                job_id=self.job_id,
                status=self.status,
                report_name=self.report_name,
                job_start_time=self.job_start_time,
                job_finish_time=self.job_finish_time,
                update_time=self.update_time,
                report_title=self.report_title,
                overrides=self.overrides,
                mailto=self.mailto,
                email_subject=self.email_subject,
                generate_pdf_output=self.generate_pdf_output,
                hide_code=self.hide_code,
            )
        )
