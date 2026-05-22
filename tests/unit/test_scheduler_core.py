import mock
import pytest

from notebooker.constants import DEFAULT_SERIALIZER, DEFAULT_DATABASE_NAME, DEFAULT_RESULT_COLLECTION_NAME
from notebooker.settings import WebappConfig
from notebooker.scheduler_core import get_jobstore_config, create_scheduler, create_blocking_scheduler


class TestGetJobstoreConfig:
    def test_extracts_config_from_serializer(self, webapp_config):
        """Test that get_jobstore_config extracts correct values from serializer."""
        config = get_jobstore_config(webapp_config)

        assert "client" in config
        assert config["client"] is not None
        assert config["database"] == DEFAULT_DATABASE_NAME
        assert config["collection"] == f"{DEFAULT_RESULT_COLLECTION_NAME}_scheduler"

    def test_respects_custom_database_override(self, webapp_config):
        """Test that custom scheduler database is respected."""
        webapp_config.SCHEDULER_MONGO_DATABASE = "custom_db"
        config = get_jobstore_config(webapp_config)

        assert config["database"] == "custom_db"
        assert config["collection"] == f"{DEFAULT_RESULT_COLLECTION_NAME}_scheduler"

    def test_respects_custom_collection_override(self, webapp_config):
        """Test that custom scheduler collection is respected."""
        webapp_config.SCHEDULER_MONGO_COLLECTION = "custom_scheduler_coll"
        config = get_jobstore_config(webapp_config)

        assert config["database"] == DEFAULT_DATABASE_NAME
        assert config["collection"] == "custom_scheduler_coll"

    def test_raises_for_non_mongo_serializer(self):
        """Test that a non-Mongo serializer raises ValueError."""
        config = WebappConfig(SERIALIZER_CLS="PyMongoResultSerializer", SERIALIZER_CONFIG={})  # valid but we'll mock it

        # Mock get_serializer_from_cls to return a non-Mongo serializer (just a mock object)
        with mock.patch("notebooker.scheduler_core.get_serializer_from_cls") as mock_get_serializer:
            mock_get_serializer.return_value = mock.MagicMock()  # Not a MongoResultSerializer
            with pytest.raises(ValueError, match="Mongo Result serializer"):
                get_jobstore_config(config)


class TestCreateScheduler:
    def test_creates_running_scheduler(self):
        """Test that create_scheduler creates a running scheduler."""
        mock_client = mock.MagicMock()
        jobstore_config = {"client": mock_client, "database": "test_db", "collection": "test_scheduler"}

        with mock.patch("notebooker.scheduler_core.BackgroundScheduler") as mock_scheduler_cls:
            with mock.patch("notebooker.scheduler_core.MongoDBJobStore") as mock_jobstore_cls:
                mock_scheduler = mock.MagicMock()
                mock_scheduler_cls.return_value = mock_scheduler

                scheduler = create_scheduler(jobstore_config, paused=False)

                # Verify jobstore was created with correct params
                mock_jobstore_cls.assert_called_once_with(
                    database="test_db", collection="test_scheduler", client=mock_client
                )

                # Verify scheduler was started but not paused
                mock_scheduler.start.assert_called_once()
                mock_scheduler.pause.assert_not_called()
                mock_scheduler.print_jobs.assert_called_once()

                assert scheduler is mock_scheduler

    def test_creates_paused_scheduler(self):
        """Test that create_scheduler with paused=True starts scheduler in paused state."""
        mock_client = mock.MagicMock()
        jobstore_config = {"client": mock_client, "database": "test_db", "collection": "test_scheduler"}

        with mock.patch("notebooker.scheduler_core.BackgroundScheduler") as mock_scheduler_cls:
            with mock.patch("notebooker.scheduler_core.MongoDBJobStore"):
                mock_scheduler = mock.MagicMock()
                mock_scheduler_cls.return_value = mock_scheduler

                scheduler = create_scheduler(jobstore_config, paused=True)

                # Verify scheduler was started with paused=True (no race condition)
                mock_scheduler.start.assert_called_once_with(paused=True)

                assert scheduler is mock_scheduler

    def test_scheduler_created_with_correct_defaults(self):
        """Test that scheduler is created with correct job defaults."""
        mock_client = mock.MagicMock()
        jobstore_config = {"client": mock_client, "database": "test_db", "collection": "test_scheduler"}

        with mock.patch("notebooker.scheduler_core.BackgroundScheduler") as mock_scheduler_cls:
            with mock.patch("notebooker.scheduler_core.MongoDBJobStore"):
                mock_scheduler = mock.MagicMock()
                mock_scheduler_cls.return_value = mock_scheduler

                create_scheduler(jobstore_config)

                # Verify misfire_grace_time is set to 1 hour
                call_kwargs = mock_scheduler_cls.call_args[1]
                assert call_kwargs["job_defaults"] == {"misfire_grace_time": 60 * 60}


class TestCreateBlockingScheduler:
    def test_creates_blocking_scheduler_without_starting(self):
        """create_blocking_scheduler builds a BlockingScheduler with the right jobstore but does NOT start it."""
        mock_client = mock.MagicMock()
        jobstore_config = {"client": mock_client, "database": "test_db", "collection": "test_scheduler"}

        with mock.patch("notebooker.scheduler_core.BlockingScheduler") as mock_scheduler_cls:
            with mock.patch("notebooker.scheduler_core.MongoDBJobStore") as mock_jobstore_cls:
                mock_scheduler = mock.MagicMock()
                mock_scheduler_cls.return_value = mock_scheduler

                scheduler = create_blocking_scheduler(jobstore_config)

                mock_jobstore_cls.assert_called_once_with(
                    database="test_db", collection="test_scheduler", client=mock_client
                )

                # Caller is responsible for .start() - we should not have called it.
                mock_scheduler.start.assert_not_called()

                call_kwargs = mock_scheduler_cls.call_args[1]
                assert call_kwargs["job_defaults"] == {"misfire_grace_time": 60 * 60}

                assert scheduler is mock_scheduler
