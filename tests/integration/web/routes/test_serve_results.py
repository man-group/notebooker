import datetime
import json
import re
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from notebooker.constants import JobStatus, NotebookResultComplete
from notebooker.settings import WebappConfig
from notebooker.web.app import create_app
from notebooker.web.routes.serve_results import _render_results


def test_clone_url_encodes_hash_in_json_parameters():
    app = create_app(WebappConfig(DISABLE_SCHEDULER=True))
    app.config.update(
        DEFAULT_MAILFROM="",
        DISABLE_SCHEDULER=True,
        READONLY_MODE=False,
    )
    result = NotebookResultComplete(
        job_id="job1",
        report_name="report_name",
        report_title="Report Name",
        job_start_time=datetime.datetime(2020, 1, 1),
        job_finish_time=datetime.datetime(2020, 1, 1, 1),
        raw_html_resources={},
        raw_html="",
        status=JobStatus.DONE,
        overrides={"slack_channel": "#my-fab-channel"},
    )

    with app.test_request_context():
        with mock.patch("notebooker.web.routes.serve_results.get_all_possible_templates", return_value={}):
            rv = _render_results("job1", "report_name", result)

    clone_url_match = re.search(r"cloneReport\('([^']+)'\)", rv)
    assert clone_url_match is not None
    clone_url = clone_url_match.group(1)
    assert urlsplit(clone_url).fragment == ""
    assert json.loads(parse_qs(urlsplit(clone_url).query)["json_params"][0]) == result.overrides
