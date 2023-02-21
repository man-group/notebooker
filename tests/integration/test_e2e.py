# End to end testing
import datetime

import freezegun
import pytest

from notebooker.constants import JobStatus
from notebooker.web.routes.report_execution import _rerun_report
from notebooker.execute_notebook import run_report_in_subprocess
from notebooker.web.utils import get_serializer


def _get_report_output(job_id, serialiser):
    while True:
        result = serialiser.get_check_result(job_id)
        if result.status not in (JobStatus.PENDING, JobStatus.SUBMITTED):
            break
    return result


def _check_report_output(job_id, serialiser, **kwargs):
    result = _get_report_output(job_id, serialiser)
    assert result.status == JobStatus.DONE, result.error_info
    assert result.stdout
    assert result.raw_html
    assert result.email_html
    assert result.raw_ipynb_json
    assert result.pdf == ""
    assert result.job_start_time < result.job_finish_time
    for k, v in kwargs.items():
        assert getattr(result, k) == v, "Report output for attribute {} was incorrect!".format(k)


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report(
    bson_library, flask_app, webapp_config, setup_and_cleanup_notebooker_filesystem, setup_workspace, report_name
):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_title = "my report title"
        mailto = ""
        job_id = run_report_in_subprocess(
            webapp_config,
            report_name,
            report_title,
            mailto,
            overrides,
            generate_pdf_output=False,
            prepare_only=True,
            run_synchronously=True,
        )
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
def test_run_failing_report(
    bson_library, flask_app, webapp_config, setup_and_cleanup_notebooker_filesystem, setup_workspace
):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_name = "fake/report_failing"
        report_title = "my report title"
        mailto = ""
        with pytest.raises(RuntimeError, match=".*The report execution failed with exit code .*"):
            run_report_in_subprocess(
                webapp_config,
                report_name,
                report_title,
                mailto,
                overrides,
                generate_pdf_output=False,
                prepare_only=False,
                run_synchronously=True,
                n_retries=0,
            )
        job_id = bson_library.find_one()["job_id"]
        result = _get_report_output(job_id, serialiser)
        assert result.status == JobStatus.ERROR
        assert result.error_info
        assert result.stdout


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report_and_rerun(
    bson_library, flask_app, webapp_config, setup_and_cleanup_notebooker_filesystem, setup_workspace, report_name
):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_title = "my report title"
        mailto = ""
        job_id = run_report_in_subprocess(
            webapp_config,
            report_name,
            report_title,
            mailto,
            overrides,
            generate_pdf_output=False,
            prepare_only=True,
            run_synchronously=True,
        )
        _check_report_output(
            job_id,
            serialiser,
            overrides=overrides,
            report_name=report_name,
            report_title=report_title,
            mailto=mailto,
            generate_pdf_output=False,
        )

        new_job_id = _rerun_report(job_id, prepare_only=True, run_synchronously=True)
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


@pytest.mark.parametrize("report_name", ["fake/py_report", "fake/ipynb_report"])
@freezegun.freeze_time(datetime.datetime(2018, 1, 12))
def test_run_report_hide_code(
    bson_library, flask_app, webapp_config, setup_and_cleanup_notebooker_filesystem, setup_workspace, report_name
):
    with flask_app.app_context():
        serialiser = get_serializer()
        overrides = {"n_points": 5}
        report_title = "my report title"
        mailto = ""
        job_id = run_report_in_subprocess(
            webapp_config,
            report_name,
            report_title,
            mailto,
            overrides,
            hide_code=True,
            generate_pdf_output=False,
            prepare_only=True,
            run_synchronously=True,
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
