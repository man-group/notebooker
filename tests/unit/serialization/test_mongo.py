from unittest.mock import Mock, MagicMock

from mock import patch

from notebooker.serialization.mongo import JobStatus, MongoResultSerializer


def test_mongo_filter():
    mongo_filter = MongoResultSerializer._mongo_filter("report")
    assert mongo_filter == {"report_name": "report"}


def test_mongo_filter_overrides():
    mongo_filter = MongoResultSerializer._mongo_filter("report", overrides={"b": 1, "a": 2})
    assert mongo_filter == {"report_name": "report", "overrides.a": 2, "overrides.b": 1}


def test_mongo_filter_status():
    mongo_filter = MongoResultSerializer._mongo_filter("report", status=JobStatus.DONE)
    assert mongo_filter == {"report_name": "report", "status": JobStatus.DONE.value}


@patch("notebooker.serialization.mongo.gridfs")
@patch("notebooker.serialization.mongo.MongoResultSerializer.get_mongo_database")
@patch("notebooker.serialization.mongo.MongoResultSerializer._get_all_job_ids")
@patch("notebooker.serialization.mongo.MongoResultSerializer.get_mongo_connection")
def test_get_latest_job_id_for_name_and_params(conn, _get_all_job_ids, db, gridfs):
    serializer = MongoResultSerializer()
    serializer.get_latest_job_id_for_name_and_params("report_name", None)
    _get_all_job_ids.assert_called_once_with("report_name", None, as_of=None, limit=1)


@patch("notebooker.serialization.mongo.gridfs")
@patch("notebooker.serialization.mongo.MongoResultSerializer.get_mongo_database")
@patch("notebooker.serialization.mongo.MongoResultSerializer.get_mongo_connection")
def test__get_all_job_ids(conn, db, gridfs):
    serializer = MongoResultSerializer()
    serializer._get_all_job_ids("report_name", None, limit=1)
    serializer.library.aggregate.assert_called_once_with(
        [
            {"$match": {"status": {"$ne": JobStatus.DELETED.value}, "report_name": "report_name"}},
            {"$sort": {"update_time": -1}},
            {"$limit": 1},
            {"$project": {"report_name": 1, "job_id": 1}},
        ]
    )


@patch("notebooker.serialization.mongo.gridfs")
@patch("notebooker.serialization.mongo.MongoResultSerializer.get_mongo_database")
@patch("notebooker.serialization.mongo.MongoResultSerializer.get_mongo_connection")
def test_delete_result_dry_run(mock_conn, mock_db, mock_gridfs):
    # Setup
    serializer = MongoResultSerializer()
    mock_result = {
        "job_id": "test_job",
        "status": JobStatus.DONE.value,
        "raw_html_resources": {"outputs": ["file1.html"]},
        "generate_pdf_output": True,
    }

    serializer._get_raw_check_result = Mock(return_value=mock_result)
    mock_gridfs_instance = MagicMock()
    serializer.result_data_store = mock_gridfs_instance
    mock_gridfs_instance.find.return_value = [Mock(_id="id1")]

    # Execute with dry_run=True
    result = serializer.delete_result("test_job", dry_run=True)

    # Verify no actual deletions occurred
    assert not serializer.library.find_one_and_update.called
    assert not mock_gridfs_instance.delete.called

    # But verify the result contains what would be deleted
    assert result["deleted_result_document"] == mock_result
    assert len(result["gridfs_filenames"]) > 0
