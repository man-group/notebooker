import datetime
import uuid

import pytest

from notebooker.constants import JobStatus, NotebookResultComplete, NotebookResultError
from notebooker.serialization.serialization import initialize_serializer_from_config
from notebooker.utils.filesystem import initialise_base_dirs


def test_mongo_saving_ipynb_json_to_gridfs(bson_library, webapp_config):
    initialise_base_dirs(webapp_config=webapp_config)
    serializer = initialize_serializer_from_config(webapp_config)

    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer.save_check_result(
        NotebookResultComplete(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.DONE,
            update_time=datetime.datetime(2018, 1, 12, 2, 32),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_finish_time=datetime.datetime(2018, 1, 12, 2, 58),
            raw_ipynb_json="x" * 32 * (2**20),  # 16MB document max
            raw_html="x" * 32 * (2**20),  # 16MB document max
            email_html="x" * 32 * (2**20),  # 16MB document max
            pdf=b"x" * 32 * (2**20),  # 16MB document max
            raw_html_resources={"inlining": {"big_thing": "a" * 32 * (2**20)}},
        )
    )
    result = serializer.get_check_result(job_id)
    assert result.raw_ipynb_json
    assert result.raw_html
    assert result.email_html
    assert result.pdf
    assert result.raw_html_resources["inlining"]


def test_cant_serialise_done_job_via_update(bson_library, webapp_config):
    job_id = str(uuid.uuid4())
    serializer = initialize_serializer_from_config(webapp_config)
    with pytest.raises(ValueError, match=".*should not be called with a completed job.*"):
        serializer.update_check_status(
            job_id,
            JobStatus.DONE,
            raw_html_resources={"outputs": {}},
            job_finish_time=datetime.datetime.now(),
            pdf="",
            raw_ipynb_json="[]",
            raw_html="",
            email_html="",
        )


def test_delete(bson_library, webapp_config):
    initialise_base_dirs(webapp_config=webapp_config)
    serializer = initialize_serializer_from_config(webapp_config)

    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    raw_html = "x" * 32 * (2**20)
    serializer.save_check_result(
        NotebookResultComplete(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=JobStatus.DONE,
            update_time=datetime.datetime(2018, 1, 12, 2, 32),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            job_finish_time=datetime.datetime(2018, 1, 12, 2, 58),
            raw_ipynb_json="x" * 32 * (2**20),  # 16MB document max
            raw_html=raw_html,  # 16MB document max
            email_html="x" * 32 * (2**20),  # 16MB document max
            pdf=b"x" * 32 * (2**20),  # 16MB document max
            raw_html_resources={"inlining": {"big_thing": "a" * 32 * (2**20)}, "other_stuff": "Yep"},
        )
    )
    assert bson_library.find_one({"job_id": job_id}) is not None
    result = serializer.get_check_result(job_id)
    assert result is not None
    assert result.raw_html == raw_html
    deleted_stuff = serializer.delete_result(job_id)
    assert [r for r in serializer.result_data_store.list()] == []
    for filename in deleted_stuff["gridfs_filenames"]:
        assert serializer.result_data_store.exists(filename=filename) is False
    assert serializer.get_check_result(job_id) is None


@pytest.mark.parametrize("job_status", [JobStatus.CANCELLED, JobStatus.TIMEOUT, JobStatus.ERROR])
def test_delete_error(bson_library, webapp_config, job_status):
    initialise_base_dirs(webapp_config=webapp_config)
    serializer = initialize_serializer_from_config(webapp_config)

    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer.save_check_result(
        NotebookResultError(
            job_id=job_id,
            report_name=report_name,
            report_title=report_name,
            status=job_status,
            update_time=datetime.datetime(2018, 1, 12, 2, 32),
            job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
            error_info="Oh no!",
        )
    )
    assert bson_library.find_one({"job_id": job_id}) is not None
    result = serializer.get_check_result(job_id)
    assert result is not None
    deleted_stuff = serializer.delete_result(job_id)
    assert [r for r in serializer.result_data_store.list()] == []
    for filename in deleted_stuff["gridfs_filenames"]:
        assert serializer.result_data_store.exists(filename=filename) is False
    assert serializer.get_check_result(job_id) is None
