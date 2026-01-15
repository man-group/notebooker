import mock

from notebooker.web.app import setup_scheduler


def test_setup_scheduler_disabled(flask_app, webapp_config):
    webapp_config.DISABLE_SCHEDULER = True
    app = setup_scheduler(flask_app, webapp_config)
    assert app.apscheduler is None


def test_setup_scheduler(flask_app, webapp_config, test_db_name, test_lib_name):
    webapp_config.DISABLE_SCHEDULER = False
    scheduler_coll = f"{test_lib_name}_scheduler"
    with mock.patch("notebooker.scheduler_core.BackgroundScheduler") as sched:
        with mock.patch("notebooker.scheduler_core.MongoDBJobStore") as jobstore:
            app = setup_scheduler(flask_app, webapp_config)
            assert app.apscheduler is not None
            jobstore.assert_called_with(database=test_db_name, collection=scheduler_coll, client=mock.ANY)


def test_setup_scheduler_management_only(flask_app, webapp_config, test_db_name, test_lib_name):
    """Test that SCHEDULER_MANAGEMENT_ONLY starts scheduler in paused state."""
    webapp_config.DISABLE_SCHEDULER = False
    webapp_config.SCHEDULER_MANAGEMENT_ONLY = True
    scheduler_coll = f"{test_lib_name}_scheduler"
    with mock.patch("notebooker.scheduler_core.BackgroundScheduler") as sched_cls:
        with mock.patch("notebooker.scheduler_core.MongoDBJobStore") as jobstore:
            mock_scheduler = mock.MagicMock()
            sched_cls.return_value = mock_scheduler

            app = setup_scheduler(flask_app, webapp_config)

            assert app.apscheduler is not None
            # Verify scheduler was started with paused=True (no race condition)
            mock_scheduler.start.assert_called_once_with(paused=True)
            jobstore.assert_called_with(database=test_db_name, collection=scheduler_coll, client=mock.ANY)
