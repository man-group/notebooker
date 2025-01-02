import json
import pytest


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
def test_create_schedule(flask_app, setup_workspace, report_name):
    with flask_app.test_client() as client:
        rv = client.post(
            f"/scheduler/create/{report_name}",
            data={
                "report_title": "test2",
                "report_name": report_name,
                "overrides": "",
                "mailto": "",
                "error_mailto": "",
                "generate_pdf": True,
                "is_slideshow": True,
                "cron_schedule": "* * * * *",
                "mailfrom": "test@example.com",
                "email_subject": "Subject",
            },
        )
        assert rv.status_code == 201
        data = json.loads(rv.data)
        assert data.pop("next_run_time")
        assert data == {
            "cron_schedule": "* * * * *",
            "delete_url": f"/scheduler/{report_name}_test2",
            "id": f"{report_name}_test2",
            "params": {
                "generate_pdf": True,
                "hide_code": False,
                "mailto": "",
                "error_mailto": "",
                "overrides": "",
                "report_name": report_name,
                "report_title": "test2",
                "is_slideshow": True,
                "scheduler_job_id": f"{report_name}_test2",
                "mailfrom": "test@example.com",
                "email_subject": "Subject",
            },
            "trigger": {
                "fields": {
                    "day": ["*"],
                    "day_of_week": ["*"],
                    "hour": ["*"],
                    "minute": ["*"],
                    "month": ["*"],
                    "second": ["0"],
                    "week": ["*"],
                    "year": ["*"],
                }
            },
        }


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
def test_scheduler_handles_booleans_properly(flask_app, setup_workspace, report_name):
    with flask_app.test_client() as client:
        rv = client.post(
            f"/scheduler/create/{report_name}",
            data={
                "report_title": "test2",
                "report_name": report_name,
                "overrides": "",
                "mailto": "",
                "error_mailto": "",
                "generate_pdf": True,
                "hide_code": True,
                "is_slideshow": True,
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201
        data = json.loads(rv.data)
        assert data.pop("next_run_time")
        assert data["params"]["generate_pdf"] is True
        assert data["params"]["hide_code"] is True
        assert data["params"]["is_slideshow"] is True


def test_create_schedule_bad_report_name(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.post(
            "/scheduler/create/fake2",
            data={
                "report_title": "test2",
                "report_name": "fake2",
                "overrides": "",
                "mailto": "",
                "is_slideshow": True,
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 404


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
def test_list_scheduled_jobs(flask_app, setup_workspace, report_name):
    with flask_app.test_client() as client:
        rv = client.post(
            f"/scheduler/create/{report_name}",
            data={
                "report_title": "test2",
                "report_name": report_name,
                "overrides": "",
                "mailto": "",
                "is_slideshow": True,
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201

        rv = client.get("/scheduler/jobs")
        assert rv.status_code == 200
        jobs = json.loads(rv.data)
        assert len(jobs) == 1
        assert jobs[0]["id"] == f"{report_name}_test2"


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
def test_delete_scheduled_jobs(flask_app, setup_workspace, report_name):
    with flask_app.test_client() as client:
        rv = client.post(
            f"/scheduler/create/{report_name}",
            data={
                "report_title": "test2",
                "report_name": report_name,
                "overrides": "",
                "mailto": "",
                "is_slideshow": True,
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201

        rv = client.get("/scheduler/jobs")
        assert rv.status_code == 200
        assert len(json.loads(rv.data)) == 1

        rv = client.delete(f"/scheduler/{report_name}_test2")
        assert rv.status_code == 200

        rv = client.get("/scheduler/jobs")
        assert rv.status_code == 200
        assert len(json.loads(rv.data)) == 0
