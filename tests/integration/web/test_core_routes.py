import json
import notebooker.version


def test_create_schedule(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get(
            "/core/all_possible_templates_flattened",
        )
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"result": ["fake/report", "fake/report_failing", "fake/ipynb_report"]}


def test_version_number(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get(
            "/core/version",
        )
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"version": notebooker.version.__version__}
