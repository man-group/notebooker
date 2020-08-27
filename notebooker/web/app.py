import atexit
import logging
import os
from typing import Optional

import sys
import threading
import time

from flask import Flask
from gevent.pywsgi import WSGIServer

from notebooker.constants import CANCEL_MESSAGE, JobStatus
from notebooker.serialization.serialization import get_fresh_serializer, serializer_kwargs_from_os_envs
from notebooker.utils.filesystem import _cleanup_dirs, initialise_base_dirs
from notebooker.web.converters import DateConverter
from notebooker.web.report_hunter import _report_hunter
from notebooker.web.routes.core import core_bp
from notebooker.web.routes.index import index_bp
from notebooker.web.routes.pending_results import pending_results_bp
from notebooker.web.routes.run_report import run_report_bp
from notebooker.web.routes.serve_results import serve_results_bp

logger = logging.getLogger(__name__)
all_report_refresher: Optional[threading.Thread] = None


def _cancel_all_jobs():
    serializer = get_fresh_serializer()
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
    _cleanup_dirs()
    if all_report_refresher:
        # Wait until it terminates.
        logger.info('Stopping "report hunter" thread.')
        all_report_refresher.join()
    # Allow all clients looking for task results to get the bad news...
    time.sleep(2)


def start_app(serializer):
    global all_report_refresher
    if os.getenv("NOTEBOOKER_APP_STOPPING"):
        del os.environ["NOTEBOOKER_APP_STOPPING"]
    all_report_refresher = threading.Thread(
        target=_report_hunter, args=(serializer,), kwargs=serializer_kwargs_from_os_envs()
    )
    all_report_refresher.daemon = True
    all_report_refresher.start()


def setup_env_vars():
    """
    Set up environment variables based on the NOTEBOOKER_ENVIRONMENT env var.
    These can be overridden by simply setting each env var in the first place.
    Returns a list of the environment variables which were changed.
    """
    notebooker_environment = os.getenv("NOTEBOOKER_ENVIRONMENT", "Dev")
    from .config import settings

    config = getattr(settings, f"{notebooker_environment}Config")()
    set_vars = []
    logger.info("Running Notebooker with the following params:")
    for attribute in (c for c in dir(config) if "__" not in c):
        existing = os.getenv(attribute)
        if existing is None:
            os.environ[attribute] = str(getattr(config, attribute))
            set_vars.append(attribute)
        if "PASSWORD" not in attribute:
            logger.info(f"{attribute} = {os.environ[attribute]}")
    return set_vars


def create_app():
    import pkg_resources

    flask_app = Flask(__name__, template_folder=f"{pkg_resources.resource_filename(__name__, 'templates')}")

    flask_app.url_map.converters["date"] = DateConverter
    flask_app.register_blueprint(index_bp)
    flask_app.register_blueprint(run_report_bp)
    flask_app.register_blueprint(core_bp)
    flask_app.register_blueprint(serve_results_bp)
    flask_app.register_blueprint(pending_results_bp)
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


def setup_app(flask_app):
    # Setup environment
    setup_env_vars()
    initialise_base_dirs()
    logging.basicConfig(level=logging.getLevelName(os.getenv("LOGGING_LEVEL", "INFO")))
    flask_app.config.update(
        TEMPLATES_AUTO_RELOAD=bool(os.environ["DEBUG"]), EXPLAIN_TEMPLATE_LOADING=True, DEBUG=bool(os.environ["DEBUG"])
    )
    start_app(os.environ["NOTEBOOK_SERIALIZER"])
    return flask_app


def main():
    flask_app = create_app()
    flask_app = setup_app(flask_app)
    port = int(os.environ["PORT"])
    logger.info("Notebooker is now running at http://0.0.0.0:%d", port)
    http_server = WSGIServer(("0.0.0.0", port), flask_app)
    http_server.serve_forever()


if __name__ == "__main__":
    main()
