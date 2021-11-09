import json
import notebooker.version


def test_create_schedule(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get(
            "/core/all_possible_templates_flattened",
        )
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"result": ["fake/py_report", "fake/ipynb_report", "fake/report_failing"]}


def test_version_number(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get(
            "/core/version",
        )
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"version": notebooker.version.__version__}
