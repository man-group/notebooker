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
import sys
import time

from notebooker.scheduler_core import get_jobstore_config, create_scheduler
from notebooker.settings import BaseConfig

logger = logging.getLogger(__name__)

# Global reference to scheduler for signal handler
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

    sys.exit(0)


def run_standalone_scheduler(config: BaseConfig):
    """
    Run the scheduler as a standalone process.

    This function:
    1. Sets up the GLOBAL_CONFIG for run_report() to use
    2. Creates and starts the scheduler with MongoDB jobstore
    3. Registers signal handlers for graceful shutdown
    4. Keeps the process alive until terminated

    Parameters
    ----------
    config : BaseConfig
        The notebooker configuration containing serializer settings and
        scheduler configuration (SCHEDULER_MONGO_DATABASE, SCHEDULER_MONGO_COLLECTION).
    """
    global _scheduler

    # Set up GLOBAL_CONFIG so run_report() can access it
    # This is needed because scheduled jobs call run_report() which
    # relies on GLOBAL_CONFIG being set
    from notebooker.web import app as app_module

    app_module.GLOBAL_CONFIG = config

    logger.info("Starting standalone scheduler...")

    # Get jobstore configuration from serializer
    jobstore_config = get_jobstore_config(config)

    # Create and start scheduler (not paused - we want to execute jobs)
    _scheduler = create_scheduler(jobstore_config, paused=False)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    logger.info("Standalone scheduler is running. Press Ctrl+C to stop.")

    # Keep the process alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown_handler(signal.SIGINT, None)
