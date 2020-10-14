# End to end testing
import datetime
import os

import freezegun
import git
import mock
import pytest

from notebooker.constants import JobStatus, DEFAULT_SERIALIZER
from notebooker.web.app import create_app
from notebooker.web.routes.run_report import _rerun_report, run_report
from notebooker.web.utils import get_serializer

from ..utils import setup_and_cleanup_notebooker_filesystem

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


def _setup_workspace(workspace):
    (workspace.workspace + "/templates").mkdir()
    git.Git(workspace.workspace).init()
    (workspace.workspace + "/templates/fake").mkdir()
    report_to_run = workspace.workspace + "/templates/fake/report.py"
    report_to_run.write_lines(DUMMY_REPORT.split("\n"))


def _environ(mongo_host, workspace, db_name, lib_name):
    return {
        "MONGO_HOST": mongo_host,
        "MONGO_USERNAME": None,
        "MONGO_PASSWORD": None,
        "DATABASE_NAME": db_name,
        "PY_TEMPLATE_DIR": workspace.workspace,
        "GIT_REPO_TEMPLATE_DIR": "templates",
        "RESULT_COLLECTION_NAME": lib_name,
    }


@pytest.fixture
def environ(monkeypatch, mongo_host, workspace, test_db_name, test_lib_name):
    """Setup workspace and environment variables for tests in this file."""
    _setup_workspace(workspace)
    update = _environ(mongo_host, workspace, test_db_name, test_lib_name)
    for k, v in update.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)


def _check_report_output(job_id, serialiser, **kwargs):
    while True:
        result = serialiser.get_check_result(job_id)
        if result.status not in (JobStatus.PENDING, JobStatus.SUBMITTED):
            break
    assert result.status == JobStatus.DONE, result.error_info
    assert result.stdout != ""
    assert result.raw_html
    assert result.raw_ipynb_json
    assert result.pdf == ""
    assert result.job_start_time < result.job_finish_time
    for k, v in kwargs.items():
        assert getattr(result, k) == v, "Report output for attribute {} was incorrect!".format(k)


@setup_and_cleanup_notebooker_filesystem
@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report(bson_library, environ):
    flask_app = create_app()
    with flask_app.app_context() as c:
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_name = "fake/report"
        report_title = "my report title"
        mailto = "jon@fakeemail.com"
        job_id = run_report(report_name, report_title, mailto, overrides, generate_pdf_output=False, prepare_only=True)
        _check_report_output(
            job_id, serialiser, overrides=overrides, report_name=report_name, report_title=report_title, mailto=mailto,
        )
        assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, overrides)
        assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, None)
        assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, overrides)
        assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, None)


@setup_and_cleanup_notebooker_filesystem
@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report_old(bson_library, mongo_host, workspace, test_db_name, test_lib_name):
    _setup_workspace(workspace)
    for k, v in _environ(mongo_host, workspace, test_db_name, test_lib_name).items():
        os.environ[k] = v
    try:
        flask_app = create_app()
        flask_app.config["SERIALIZER_CLS"] = DEFAULT_SERIALIZER
        flask_app.config["SERIALIZER_CONFIG"] = {"mongo_host": mongo_host, "mongo_db_name": test_db_name}
        with flask_app.app_context() as c:
            serialiser = get_serializer()
            overrides = {"n_points": 5}
            report_name = "fake/report"
            report_title = "my report title"
            mailto = "jon@fakeemail.com"
            job_id = run_report(
                report_name, report_title, mailto, overrides, generate_pdf_output=False, prepare_only=True
            )
            _check_report_output(
                job_id,
                serialiser,
                overrides=overrides,
                report_name=report_name,
                report_title=report_title,
                mailto=mailto,
            )
            assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, overrides)
            assert job_id == serialiser.get_latest_job_id_for_name_and_params(report_name, None)
            assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, overrides)
            assert job_id == serialiser.get_latest_successful_job_id_for_name_and_params(report_name, None)
    finally:
        for k, __ in _environ(mongo_host, workspace, test_db_name, test_lib_name).items():
            del os.environ[k]


@setup_and_cleanup_notebooker_filesystem
@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report_and_rerun(bson_library, environ):
    flask_app = create_app()
    with flask_app.app_context() as c:
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
