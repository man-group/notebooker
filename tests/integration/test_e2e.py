# End to end testing
import datetime
import json
import time
import mock

import freezegun
import git
import pytest

from notebooker.constants import JobStatus
from notebooker.web.routes.run_report import _rerun_report, run_report
from notebooker.web.utils import get_serializer

DUMMY_REPORT = """
# ---
# jupyter:
#   celltoolbar: Tags
#   jupytext_format_version: '1.2'
#   kernelspec:
#     display_name: spark273
#     language: python
#     name: spark273
# ---

# %matplotlib inline
import pandas as pd
import numpy as np
import random

# + {"tags": ["parameters"]}
n_points = random.choice(range(50, 1000))
# -

idx = pd.date_range('1/1/2000', periods=n_points)
df = pd.DataFrame(np.random.randn(n_points, 4), index=idx, columns=list('ABCD'))
df.plot()

cumulative = df.cumsum()
cumulative.plot()
"""


@pytest.fixture
def setup_workspace(workspace):
    (workspace.workspace + "/templates").mkdir()
    git.Git(workspace.workspace).init()
    (workspace.workspace + "/templates/fake").mkdir()
    report_to_run = workspace.workspace + "/templates/fake/report.py"
    report_to_run.write_lines(DUMMY_REPORT.split("\n"))


def _get_report_output(job_id, serialiser):
    while True:
        result = serialiser.get_check_result(job_id)
        if result.status not in (JobStatus.PENDING, JobStatus.SUBMITTED):
            break
    return result


def _check_report_output(job_id, serialiser, **kwargs):
    result = _get_report_output(job_id, serialiser)
    assert result.status == JobStatus.DONE, result.error_info
    assert result.stdout != ""
    assert result.raw_html
    assert result.email_html
    assert result.raw_ipynb_json
    assert result.pdf == ""
    assert result.job_start_time < result.job_finish_time
    for k, v in kwargs.items():
        assert getattr(result, k) == v, "Report output for attribute {} was incorrect!".format(k)


@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report(bson_library, flask_app, setup_and_cleanup_notebooker_filesystem, setup_workspace):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_name = "fake/report"
        report_title = "my report title"
        mailto = "jon@fakeemail.com"
        job_id = run_report(report_name, report_title, mailto, overrides, generate_pdf_output=False, prepare_only=True)
        _check_report_output(
            job_id, serialiser, overrides=overrides, report_name=report_name, report_title=report_title, mailto=mailto
        )

        result = _get_report_output(job_id, serialiser)
        assert "DataFrame" in result.email_html
        assert "DataFrame" in result.raw_html

        assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, overrides)
        assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, None)
        assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, overrides)
        assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, None)


@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report_and_rerun(bson_library, flask_app, setup_and_cleanup_notebooker_filesystem, setup_workspace):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_name = "fake/report"
        report_title = "my report title"
        mailto = "jon@fakeemail.com"
        job_id = run_report(report_name, report_title, mailto, overrides, generate_pdf_output=False, prepare_only=True)
        _check_report_output(
            job_id,
            serialiser,
            overrides=overrides,
            report_name=report_name,
            report_title=report_title,
            mailto=mailto,
            generate_pdf_output=False,
        )

        new_job_id = _rerun_report(job_id, prepare_only=True)
        _check_report_output(
            new_job_id,
            serialiser,
            overrides=overrides,
            report_name=report_name,
            report_title="Rerun of " + report_title,
            mailto=mailto,
            generate_pdf_output=False,
        )
        assert new_job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, overrides)
        assert not {job_id, new_job_id} - set(serialiser.get_all_job_ids_for_name_and_params(report_name, overrides))
        assert new_job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, overrides)
        assert job_id != serialiser.get_latest_successful_job_id_for_name_and_params(report_name, overrides)


@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report(bson_library, flask_app, setup_and_cleanup_notebooker_filesystem, setup_workspace):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_name = "fake/report"
        report_title = "my report title"
        mailto = "jon@fakeemail.com"
        job_id = run_report(
            report_name, report_title, mailto, overrides, hide_code=True, generate_pdf_output=False, prepare_only=True
        )
        _check_report_output(
            job_id, serialiser, overrides=overrides, report_name=report_name, report_title=report_title, mailto=mailto
        )

        result = _get_report_output(job_id, serialiser)
        assert "DataFrame" not in result.email_html
        assert "DataFrame" in result.raw_html

        assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, overrides)
        assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, None)
        assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, overrides)
        assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, None)


def test_create_schedule(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.post(
            "/scheduler/create/fake",
            data={
                "report_title": "test2",
                "report_name": "fake",
                "overrides": "",
                "mailto": "",
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201
        data = json.loads(rv.data)
        assert data.pop("next_run_time")
        assert data == {
            "cron_schedule": "* * * * *",
            "delete_url": "/scheduler/fake_test2",
            "id": "fake_test2",
            "params": {
                "generate_pdf": False,
                "hide_code": False,
                "mailto": "",
                "overrides": "",
                "report_name": "fake",
                "report_title": "test2",
                "scheduler_job_id": "fake_test2",
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


def test_create_schedule_bad_report_name(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.post(
            "/scheduler/create/fake2",
            data={
                "report_title": "test2",
                "report_name": "fake2",
                "overrides": "",
                "mailto": "",
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 404


def test_list_scheduled_jobs(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.post(
            "/scheduler/create/fake",
            data={
                "report_title": "test2",
                "report_name": "fake",
                "overrides": "",
                "mailto": "",
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201

        rv = client.get("/scheduler/jobs")
        assert rv.status_code == 200
        jobs = json.loads(rv.data)
        assert len(jobs) == 1
        assert jobs[0]["id"] == "fake_test2"


def test_delete_scheduled_jobs(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.post(
            "/scheduler/create/fake",
            data={
                "report_title": "test2",
                "report_name": "fake",
                "overrides": "",
                "mailto": "",
                "cron_schedule": "* * * * *",
            },
        )
        assert rv.status_code == 201

        rv = client.get("/scheduler/jobs")
        assert rv.status_code == 200
        assert len(json.loads(rv.data)) == 1

        rv = client.delete("/scheduler/fake_test2")
        assert rv.status_code == 200

        rv = client.get("/scheduler/jobs")
        assert rv.status_code == 200
        assert len(json.loads(rv.data)) == 0


def test_scheduler_runs_notebooks(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        def fake_post(url, params):
            path = url.replace("http://", "").split("/", 1)[1]
            client.post(f"/{path}?{params}")
            return mock.MagicMock()
        with mock.patch("notebooker.web.scheduler.requests.post", side_effect=fake_post):
            rv = client.get("/core/get_all_available_results?limit=50")
            assert len(json.loads(rv.data)) == 0

            rv = client.post(
                "/scheduler/create/fake",
                data={
                    "report_title": "test2",
                    "report_name": "fake",
                    "overrides": "",
                    "mailto": "",
                    "cron_schedule": "* * * * *",
                },
            )
            assert rv.status_code == 201

            time.sleep(60)  # this is the highest resolution for running jobs
            rv = client.get("core/get_all_available_results?limit=50")
            assert len(json.loads(rv.data)) > 0