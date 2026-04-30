"""
Shared scheduler infrastructure for Notebooker.

This module provides common functions for setting up the APScheduler-based
job scheduler, used by both the webapp (in-process or management-only mode)
and the standalone scheduler process.
"""
import logging
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore

from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.serialization.serialization import get_serializer_from_cls
from notebooker.settings import BaseConfig

logger = logging.getLogger(__name__)


def get_jobstore_config(config: BaseConfig) -> Dict[str, Any]:
    """
    Extract MongoDB jobstore configuration from the serializer config.

    Parameters
    ----------
    config : BaseConfig
        The notebooker configuration containing serializer settings.

    Returns
    -------
    dict
        A dictionary containing:
        - 'client': The MongoDB client instance
        - 'database': The database name for the scheduler
        - 'collection': The collection name for the scheduler

    Raises
    ------
    ValueError
        If the serializer is not a MongoResultSerializer.
    """
    serializer = get_serializer_from_cls(config.SERIALIZER_CLS, **config.SERIALIZER_CONFIG)
    if not isinstance(serializer, MongoResultSerializer):
        raise ValueError(
            "We cannot support scheduling if we are not using a Mongo Result serializer, "
            "since we re-use the connection details from the serializer to store metadata "
            "about scheduling."
        )

    client = serializer.get_mongo_connection()

    # Allow config overrides for database/collection, with sensible defaults
    scheduler_db = getattr(config, "SCHEDULER_MONGO_DATABASE", "") or serializer.database_name
    scheduler_collection = (
        getattr(config, "SCHEDULER_MONGO_COLLECTION", "") or f"{serializer.result_collection_name}_scheduler"
    )

    return {"client": client, "database": scheduler_db, "collection": scheduler_collection}


def create_scheduler(jobstore_config: Dict[str, Any], paused: bool = False) -> BackgroundScheduler:
    """
    Create and start a BackgroundScheduler with MongoDB jobstore.

    Parameters
    ----------
    jobstore_config : dict
        Configuration from get_jobstore_config() containing client, database, collection.
    paused : bool, optional
        If True, the scheduler is started but immediately paused. This allows
        job CRUD operations to work without actually executing jobs. Useful for
        the webapp when running in management-only mode. Default is False.

    Returns
    -------
    BackgroundScheduler
        A started (and optionally paused) scheduler instance.
    """
    jobstores = {
        "mongo": MongoDBJobStore(
            database=jobstore_config["database"],
            collection=jobstore_config["collection"],
            client=jobstore_config["client"],
        )
    }

    scheduler = BackgroundScheduler(
        jobstores=jobstores, job_defaults={"misfire_grace_time": 60 * 60}  # 1 hour grace time
    )

    if paused:
        # Start in paused state to prevent any jobs from firing
        scheduler.start(paused=True)
        logger.info("Scheduler started in paused (management-only) mode")
    else:
        scheduler.start()
        logger.info("Scheduler started")

    scheduler.print_jobs()

    return scheduler


def create_blocking_scheduler(jobstore_config: Dict[str, Any]) -> BlockingScheduler:
    """
    Create a BlockingScheduler with MongoDB jobstore for the standalone scheduler process.

    The caller is responsible for calling ``.start()`` (which blocks) after registering
    any signal handlers.
    """
    jobstores = {
        "mongo": MongoDBJobStore(
            database=jobstore_config["database"],
            collection=jobstore_config["collection"],
            client=jobstore_config["client"],
        )
    }

    scheduler = BlockingScheduler(
        jobstores=jobstores, job_defaults={"misfire_grace_time": 60 * 60}  # 1 hour grace time
    )

    return scheduler
