import json
import urllib.parse

from notebooker.web.routes.serve_results import _clone_url_with_overrides


def test_clone_url_with_overrides_encodes_hash_in_json_params():
    overrides = {"slack_channel": "#my-fab-channel"}
    clone_url = _clone_url_with_overrides("/run_report/report_name", overrides)
    parsed = urllib.parse.urlparse(clone_url)

    assert parsed.fragment == ""
    assert "%23my-fab-channel" in clone_url
    assert json.loads(urllib.parse.parse_qs(parsed.query)["json_params"][0]) == overrides
