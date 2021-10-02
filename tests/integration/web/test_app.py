import mock

from notebooker.web.app import setup_scheduler


def test_setup_scheduler_disabled(flask_app, webapp_config):
    webapp_config.DISABLE_SCHEDULER = True
    app = setup_scheduler(flask_app, webapp_config)
    assert app.apscheduler is None


def test_setup_scheduler(flask_app, webapp_config, test_db_name, test_lib_name):
    webapp_config.DISABLE_SCHEDULER = False
    scheduler_coll = f"{test_lib_name}_scheduler"
    with mock.patch("notebooker.web.app.BackgroundScheduler") as sched:
        with mock.patch("notebooker.web.app.MongoDBJobStore") as jobstore:
            app = setup_scheduler(flask_app, webapp_config)
            assert app.apscheduler is not None
            jobstore.assert_called_with(database=test_db_name, collection=scheduler_coll, client=mock.ANY)
