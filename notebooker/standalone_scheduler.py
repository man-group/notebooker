"""
Standalone scheduler process for Notebooker.

This module provides a standalone scheduler that can run separately from
the webapp, allowing for better reliability in Kubernetes deployments.
When the scheduler runs as a separate process, it can be restarted
independently without affecting the webapp.

Usage:
    notebooker-cli start-scheduler [OPTIONS]

The webapp should be started with --scheduler-management-only when using
a standalone scheduler, so that it can manage jobs without executing them.
"""
import logging
import signal
import threading
import time

from flask import Flask, jsonify
from werkzeug.serving import make_server

from notebooker.scheduler_core import get_jobstore_config, create_blocking_scheduler
from notebooker.settings import BaseConfig

logger = logging.getLogger(__name__)

# Global reference to scheduler for signal handler and liveness probe
_scheduler = None


def _shutdown_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, shutting down scheduler...")

    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown complete")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")


def _start_liveness_probe(port: int) -> None:
    app = Flask(__name__)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    @app.route("/healthz")
    def healthz():
        if _scheduler is not None and _scheduler.running:
            return jsonify({"status": "ok"})
        return jsonify({"status": "unavailable"}), 503

    server = make_server("", port, app)
    thread = threading.Thread(target=server.serve_forever, name="liveness-probe", daemon=True)
    thread.start()
    logger.info(f"Liveness probe listening on port {port}")


def _start_jobstore_poller(interval: int = 60) -> None:
    # APScheduler sleeps indefinitely when the jobstore is empty. This thread
    # periodically wakes the scheduler so it picks up jobs added externally
    # (e.g. by the webapp running in a separate process).
    def _poll():
        while True:
            time.sleep(interval)
            if _scheduler is not None and _scheduler.running:
                _scheduler.wakeup()

    thread = threading.Thread(target=_poll, name="jobstore-poller", daemon=True)
    thread.start()


def run_standalone_scheduler(config: BaseConfig):
    """
    Run the scheduler as a standalone process.

    This function:
    1. Sets up the GLOBAL_CONFIG for run_report() to use
    2. Optionally starts a liveness probe HTTP server
    3. Creates a BlockingScheduler with MongoDB jobstore
    4. Registers signal handlers for graceful shutdown
    5. Calls .start() which blocks until shutdown
    """
    global _scheduler

    from notebooker import global_config

    global_config.GLOBAL_CONFIG = config

    logging.basicConfig(level=logging.getLevelName(getattr(config, "LOGGING_LEVEL", "INFO")))
    logger.info("Starting standalone scheduler...")

    jobstore_config = get_jobstore_config(config)

    _scheduler = create_blocking_scheduler(jobstore_config)

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    liveness_port = getattr(config, "LIVENESS_PORT", 0)
    if liveness_port:
        _start_liveness_probe(liveness_port)

    _start_jobstore_poller()
    logger.info("Standalone scheduler is running. Press Ctrl+C to stop.")

    try:
        _scheduler.start()
    except KeyboardInterrupt:
        _shutdown_handler(signal.SIGINT, None)
