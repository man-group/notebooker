import json


def test_create_schedule(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get(
            "/core/all_possible_templates_flattened",
        )
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"result": ["fake/report"]}
