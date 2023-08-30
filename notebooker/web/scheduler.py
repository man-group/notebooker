import json
from typing import Optional
import urllib

import requests
from logging import getLogger

from notebooker.execute_notebook import run_report_in_subprocess
from notebooker.web.app import GLOBAL_CONFIG

logger = getLogger(__name__)


def run_report(
    report_name: str,
    overrides: dict,
    report_title: str,
    mailto: str,
    generate_pdf: bool,
    hide_code: bool,
    scheduler_job_id: str,
    # new parameters should be added below and be optional to avoid migrations
    mailfrom: Optional[str] = None,
    is_slideshow: bool = False,
    error_mailto: Optional[str] = None,
    email_subject: Optional[str] = None,
):
    """
    This is the entrypoint of the scheduler; APScheduler has to
    run a python function and so we invoke an API call from a thin wrapper.
    """
    if GLOBAL_CONFIG:
        run_report_in_subprocess(
            GLOBAL_CONFIG,
            report_name,
            report_title,
            mailto,
            error_mailto,
            overrides,
            hide_code=hide_code,
            generate_pdf_output=generate_pdf,
            prepare_only=False,
            scheduler_job_id=scheduler_job_id,
            run_synchronously=True,
            mailfrom=mailfrom,
            n_retries=0,
            is_slideshow=is_slideshow,
            email_subject=email_subject,
        )
    else:
        # Fall back to using API. This will not work in readonly mode.
        url = f"http://localhost/run_report_json/{report_name}"
        payload = {
            "overrides": json.dumps(overrides),
            "report_title": report_title,
            "mailto": mailto,
            "error_mailto": error_mailto,
            "generate_pdf": generate_pdf,
            "hide_code": hide_code,
            "scheduler_job_id": scheduler_job_id,
            "is_slideshow": is_slideshow,
        }
        # This means that, if the default mailfrom changes, all already scheduled
        # jobs will use the new default in subsequent runs. Another approach could
        # be to fix the mailfrom to the current default, but that seems a bit less
        # natural.
        if mailfrom:
            payload["mailfrom"] = mailfrom
        if email_subject:
            payload["email_subject"] = email_subject
        logger.info(f"Running report at {url}, payload = {payload}")
        result = requests.post(url, params=urllib.parse.urlencode(payload))
        logger.info(result.content)
        result.raise_for_status()
