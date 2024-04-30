import datetime
import json

import freezegun

import notebooker.version
from notebooker.constants import NotebookResultError, NotebookResultComplete, JobStatus
from notebooker.web.utils import get_serializer
from .helpers import insert_fake_results


def test_create_schedule(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get("/core/all_possible_templates_flattened")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"result": ["fake/py_report", "fake/ipynb_report", "fake/report_failing"]}


def test_version_number(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        rv = client.get("/core/version")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == {"version": notebooker.version.__version__}


def test_insert_fake_results(flask_app, setup_workspace):
    # Is this too meta...? :-)
    results = [
        NotebookResultComplete(
            job_id="job1",
            report_name="report_name",
            job_start_time=datetime.datetime(2020, 1, 1),
            job_finish_time=datetime.datetime(2020, 1, 1, 1),
            raw_html_resources={},
            status=JobStatus.DONE,
            overrides={"param1": "big"},
            scheduler_job_id="ohboy_it's_a_schedule",
        ),
        NotebookResultError(
            job_id="job2",
            report_name="report_name",
            job_start_time=datetime.datetime(2021, 1, 2),
            status=JobStatus.ERROR,
            overrides={"param1": "small"},
        ),
    ]
    insert_fake_results(flask_app, results)
    with flask_app.app_context() as ctx:
        serializer = get_serializer()
        res = list(serializer._get_raw_results({}, {"_id": 0, "job_id": 1, "status": 1, "job_start_time": 1}, 0))
        assert sorted(res, key=lambda item: item["job_id"]) == [
            {"job_id": "job1", "status": JobStatus.DONE.value, "job_start_time": datetime.datetime(2020, 1, 1)},
            {"job_id": "job2", "status": JobStatus.ERROR.value, "job_start_time": datetime.datetime(2021, 1, 2)},
        ]


def test_get_all_templates_with_results(flask_app, setup_workspace):
    results = [
        NotebookResultComplete(
            job_id="job1",
            report_name="report_name",
            job_start_time=datetime.datetime(2020, 1, 1),
            job_finish_time=datetime.datetime(2020, 1, 1, 1),
            raw_html_resources={},
            status=JobStatus.DONE,
            overrides={"param1": "big"},
            scheduler_job_id="ohboy_it's_a_schedule",
        ),
        NotebookResultError(
            job_id="job2",
            report_name="report_name",
            job_start_time=datetime.datetime(2021, 1, 2),
            status=JobStatus.ERROR,
            overrides={"param1": "small"},
        ),
    ]
    insert_fake_results(flask_app, results)
    with freezegun.freeze_time(datetime.datetime(2021, 2, 2)):
        with flask_app.test_client() as client:
            with flask_app.app_context():
                rv = client.get("/core/get_all_templates_with_results/folder/")
                assert rv.status_code == 200, rv.data
                data = json.loads(rv.data)
                assert data == {
                    "Report Name": {
                        "count": 2,
                        "scheduler_runs": 1,
                        "report_name": "report_name",
                        "latest_run": "Sat, 02 Jan 2021 00:00:00 GMT",
                        "time_diff": "1 month",
                    }
                }


def test_get_all_templates_with_results_filtering(flask_app, setup_workspace):
    results = [
        NotebookResultComplete(
            job_id="job1",
            report_name="f1/report1",
            job_start_time=datetime.datetime(2020, 1, 1),
            job_finish_time=datetime.datetime(2020, 1, 1, 1),
            status=JobStatus.DONE,
        ),
        NotebookResultComplete(
            job_id="job2",
            report_name="f1/fsub1/report2",
            job_start_time=datetime.datetime(2020, 1, 1),
            job_finish_time=datetime.datetime(2020, 1, 1, 1),
            status=JobStatus.DONE,
        ),
        NotebookResultComplete(
            job_id="job3",
            report_name="f2/report3",
            job_start_time=datetime.datetime(2020, 1, 1),
            job_finish_time=datetime.datetime(2020, 1, 1, 1),
            status=JobStatus.DONE,
        ),
    ]
    insert_fake_results(flask_app, results)
    with freezegun.freeze_time(datetime.datetime(2021, 2, 2)):
        with flask_app.test_client() as client:
            with flask_app.app_context():
                rv = client.get("/core/get_all_templates_with_results/folder/f1/")
                assert rv.status_code == 200, rv.data
                data = json.loads(rv.data)
                assert set(data.keys()) == {"F1/Report1", "F1/Fsub1/Report2"}

                rv = client.get("/core/get_all_templates_with_results/folder/f1/fsub1")
                assert rv.status_code == 200, rv.data
                assert set(json.loads(rv.data).keys()) == {"F1/Fsub1/Report2"}

                rv = client.get("/core/get_all_templates_with_results/folder/f2/")
                assert rv.status_code == 200, rv.data
                assert set(json.loads(rv.data).keys()) == {"F2/Report3"}

                rv = client.get("/core/get_all_templates_with_results/folder/")
                assert rv.status_code == 200, rv.data
                assert set(json.loads(rv.data).keys()) == {"F1/Report1", "F1/Fsub1/Report2", "F2/Report3"}


def test_get_all_templates_with_results_no_results(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        with flask_app.app_context():
            rv = client.get("/core/get_all_templates_with_results/folder/")
            assert rv.status_code == 200, rv.data
            data = json.loads(rv.data)
            assert data == {}


def test_get_all_templates_with_results_then_delete(flask_app, setup_workspace):
    results = [
        NotebookResultComplete(
            job_id="job1",
            report_name="report_name",
            job_start_time=datetime.datetime(2020, 1, 1),
            job_finish_time=datetime.datetime(2020, 1, 1, 1),
            raw_html_resources={},
            status=JobStatus.DONE,
            overrides={"param1": "big"},
            scheduler_job_id="ohboy_it's_a_schedule",
        ),
        NotebookResultError(
            job_id="job2",
            report_name="report_name",
            job_start_time=datetime.datetime(2021, 1, 2),
            status=JobStatus.ERROR,
            overrides={"param1": "small"},
        ),
        NotebookResultError(
            job_id="job3",
            report_name="BadReport",
            job_start_time=datetime.datetime(2014, 1, 2),
            status=JobStatus.ERROR,
            overrides={"param1": "small"},
        ),
    ]
    insert_fake_results(flask_app, results)
    with freezegun.freeze_time(datetime.datetime(2021, 2, 2)):
        with flask_app.test_client() as client:
            with flask_app.app_context():
                rv = client.get("/core/get_all_templates_with_results/folder/")
                assert rv.status_code == 200, rv.data
                data = json.loads(rv.data)
                assert data == {
                    "Bad Report": {
                        "count": 1,
                        "scheduler_runs": 0,
                        "report_name": "BadReport",
                        "latest_run": "Thu, 02 Jan 2014 00:00:00 GMT",
                        "time_diff": "7 years",
                    },
                    "Report Name": {
                        "count": 2,
                        "scheduler_runs": 1,
                        "report_name": "report_name",
                        "latest_run": "Sat, 02 Jan 2021 00:00:00 GMT",
                        "time_diff": "1 month",
                    },
                }
                rv = client.post("/delete_report/job1")
                assert rv.status_code == 200, rv.data
                rv = client.post("/delete_report/job3")
                assert rv.status_code == 200, rv.data
                rv = client.get("/core/get_all_templates_with_results/folder/")
                assert rv.status_code == 200, rv.data
                data = json.loads(rv.data)
                assert data == {
                    "Report Name": {
                        "count": 1,
                        "scheduler_runs": 0,
                        "report_name": "report_name",
                        "latest_run": "Sat, 02 Jan 2021 00:00:00 GMT",
                        "time_diff": "1 month",
                    }
                }
