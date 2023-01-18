import json
from typing import Optional
import urllib

import requests
from logging import getLogger

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
):
    """
    This is the entrypoint of the scheduler; APScheduler has to
    run a python function and so we invoke an API call from a thin wrapper.
    """
    if GLOBAL_CONFIG is None:
        url = f"http://localhost/run_report_json/{report_name}"
    else:
        url = f"http://localhost:{GLOBAL_CONFIG.PORT}/run_report_json/{report_name}"
    payload = {
        "overrides": json.dumps(overrides),
        "report_title": report_title,
        "mailto": mailto,
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
    logger.info(f"Running report at {url}, payload = {payload}")
    result = requests.post(url, params=urllib.parse.urlencode(payload))
    logger.info(result.content)
    result.raise_for_status()
