"""
Integration test proving the shared MongoDB jobstore contract between the
management-only webapp scheduler and a standalone scheduler process.

The webapp runs its scheduler in paused (management-only) mode and creates
jobs via its routes. A second scheduler pointing at the same MongoDB jobstore
must see the same jobs — this is the architectural contract that lets the
standalone scheduler process pick up and execute jobs created via the webapp.
"""
import json

import pytest

from notebooker.scheduler_core import create_scheduler, get_jobstore_config
from notebooker.web.app import create_app, setup_app


@pytest.fixture
def management_only_webapp_config(webapp_config):
    webapp_config.SCHEDULER_MANAGEMENT_ONLY = True
    return webapp_config


@pytest.fixture
def management_only_flask_app(management_only_webapp_config):
    flask_app = create_app(management_only_webapp_config)
    flask_app = setup_app(flask_app, management_only_webapp_config)
    flask_app.config["DEBUG"] = True
    flask_app.config["TESTING"] = True
    return flask_app


def test_standalone_scheduler_sees_jobs_created_by_management_only_webapp(
    management_only_flask_app, management_only_webapp_config, setup_workspace
):
    report_name = "fake/py_report"
    expected_job_id = f"{report_name}_test_standalone"

    with management_only_flask_app.test_client() as client:
        rv = client.post(
            f"/scheduler/create/{report_name}",
            data={
                "report_title": "test_standalone",
                "report_name": report_name,
                "overrides": "",
                "mailto": "",
                "is_slideshow": True,
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201, rv.data
        created = json.loads(rv.data)
        assert created["id"] == expected_job_id

    webapp_jobs = management_only_flask_app.apscheduler.get_jobs()
    assert len(webapp_jobs) == 1
    assert webapp_jobs[0].id == expected_job_id

    assert management_only_flask_app.apscheduler.state == 2  # STATE_PAUSED

    jobstore_config = get_jobstore_config(management_only_webapp_config)
    standalone_scheduler = create_scheduler(jobstore_config, paused=True)
    try:
        standalone_jobs = standalone_scheduler.get_jobs()
        assert len(standalone_jobs) == 1
        assert standalone_jobs[0].id == expected_job_id
        assert standalone_jobs[0].kwargs["report_name"] == report_name
        assert standalone_jobs[0].kwargs["report_title"] == "test_standalone"
    finally:
        standalone_scheduler.shutdown(wait=False)
