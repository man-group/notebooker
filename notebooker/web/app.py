import atexit
import logging
import os
import threading
from typing import Optional

import sys
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from flask import Flask
from gevent.pywsgi import WSGIServer

from notebooker.constants import CANCEL_MESSAGE, JobStatus
from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.serialization.serialization import initialize_serializer_from_config, get_serializer_from_cls
from notebooker.settings import WebappConfig
from notebooker.utils.filesystem import _cleanup_dirs, initialise_base_dirs
from notebooker.web.converters import DateConverter
from notebooker.web.report_hunter import _report_hunter
from notebooker.web.routes.core import core_bp
from notebooker.web.routes.index import index_bp
from notebooker.web.routes.pending_results import pending_results_bp
from notebooker.web.routes.run_report import run_report_bp
from notebooker.web.routes.scheduling import scheduling_bp
from notebooker.web.routes.serve_results import serve_results_bp

logger = logging.getLogger(__name__)
all_report_refresher: Optional[threading.Thread] = None
GLOBAL_CONFIG: Optional[WebappConfig] = None


def _cancel_all_jobs():
    serializer = initialize_serializer_from_config(GLOBAL_CONFIG)
    all_pending = serializer.get_all_results(
        mongo_filter={"status": {"$in": [JobStatus.SUBMITTED.value, JobStatus.PENDING.value]}}
    )
    for result in all_pending:
        serializer.update_check_status(result.job_id, JobStatus.CANCELLED, error_info=CANCEL_MESSAGE)


@atexit.register
def _cleanup_on_exit():
    global all_report_refresher
    if "pytest" in sys.modules or not all_report_refresher:
        return
    os.environ["NOTEBOOKER_APP_STOPPING"] = "1"
    _cancel_all_jobs()
    _cleanup_dirs(GLOBAL_CONFIG)
    if all_report_refresher:
        # Wait until it terminates.
        logger.info('Stopping "report hunter" thread.')
        all_report_refresher.join()
    # Allow all clients looking for task results to get the bad news...
    time.sleep(2)


def start_app(webapp_config: WebappConfig):
    global all_report_refresher
    if os.getenv("NOTEBOOKER_APP_STOPPING"):
        del os.environ["NOTEBOOKER_APP_STOPPING"]
    all_report_refresher = threading.Thread(target=_report_hunter, args=(webapp_config,))
    all_report_refresher.daemon = True
    all_report_refresher.start()


def create_app(webapp_config=None):
    import pkg_resources

    flask_app = Flask(__name__, template_folder=f"{pkg_resources.resource_filename(__name__, 'templates')}")

    flask_app.url_map.converters["date"] = DateConverter
    flask_app.register_blueprint(index_bp)
    flask_app.register_blueprint(run_report_bp)
    flask_app.register_blueprint(core_bp)
    flask_app.register_blueprint(serve_results_bp)
    flask_app.register_blueprint(pending_results_bp)
    if webapp_config and not webapp_config.DISABLE_SCHEDULER:
        flask_app.register_blueprint(scheduling_bp)
    try:
        import prometheus_client
    except ImportError:
        logger.info(
            "prometheus_client is not installed, so not setting up a prometheus endpoint. "
            "If you want this functionality, install notebooker[prometheus] or pip install prometheus_client."
        )
    else:
        from notebooker.web.routes.prometheus import setup_metrics, prometheus_bp

        flask_app.register_blueprint(prometheus_bp)
        setup_metrics(flask_app)
    return flask_app


def setup_scheduler(flask_app, web_config):
    if web_config.DISABLE_SCHEDULER:
        flask_app.apscheduler = None
        return flask_app
    serializer = get_serializer_from_cls(web_config.SERIALIZER_CLS, **web_config.SERIALIZER_CONFIG)
    if isinstance(serializer, MongoResultSerializer):
        client = serializer.get_mongo_connection()
        database = web_config.SCHEDULER_MONGO_DATABASE or serializer.database_name
        collection = web_config.SCHEDULER_MONGO_COLLECTION or f"{serializer.result_collection_name}_scheduler"
        jobstores = {"mongo": MongoDBJobStore(database=database, collection=collection, client=client)}
    else:
        raise ValueError(
            "We cannot support scheduling if we are not using a Mongo Result serializer, "
            "since we re-use the connection details from the serializer to store metadata "
            "about scheduling."
        )
    scheduler = BackgroundScheduler(jobstores=jobstores, job_defaults={"misfire_grace_time": 60 * 60})
    scheduler.start()
    scheduler.print_jobs()
    flask_app.apscheduler = scheduler
    return flask_app


def setup_app(flask_app: Flask, web_config: WebappConfig):
    # Setup environment
    initialise_base_dirs(web_config)
    logging.basicConfig(level=logging.getLevelName(web_config.LOGGING_LEVEL))
    flask_app.config.from_object(web_config)
    flask_app.config.update(
        TEMPLATES_AUTO_RELOAD=web_config.DEBUG, EXPLAIN_TEMPLATE_LOADING=True, DEBUG=web_config.DEBUG
    )
    flask_app = setup_scheduler(flask_app, web_config)
    return flask_app


def main(web_config: WebappConfig):
    global GLOBAL_CONFIG
    GLOBAL_CONFIG = web_config
    flask_app = create_app(web_config)
    flask_app = setup_app(flask_app, web_config)
    start_app(web_config)
    logger.info("Notebooker is now running at http://0.0.0.0:%d", web_config.PORT)
    http_server = WSGIServer(("0.0.0.0", web_config.PORT), flask_app)
    http_server.serve_forever()
