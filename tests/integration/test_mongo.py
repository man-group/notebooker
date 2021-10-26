import datetime
import uuid

from notebooker.constants import JobStatus, NotebookResultComplete
from notebooker.serialization.serialization import initialize_serializer_from_config
from notebooker.utils.filesystem import initialise_base_dirs


def test_mongo_saving_ipynb_json_to_gridfs(bson_library, webapp_config):
    initialise_base_dirs(webapp_config=webapp_config)
    serializer = initialize_serializer_from_config(webapp_config)

    job_id = str(uuid.uuid4())
    report_name = str(uuid.uuid4())
    serializer.save_check_result(NotebookResultComplete(
        job_id=job_id,
        report_name=report_name,
        report_title=report_name,
        status=JobStatus.DONE,
        update_time=datetime.datetime(2018, 1, 12, 2, 32),
        job_start_time=datetime.datetime(2018, 1, 12, 2, 30),
        job_finish_time=datetime.datetime(2018, 1, 12, 2, 58),
        raw_ipynb_json="x"*32*(2**20),  # 16MB document max
    ))
    result = serializer.get_check_result(job_id)
    assert result.raw_ipynb_json
