import logging
import os
from enum import Enum

from notebooker.serialization.mongo import NotebookResultSerializer
from notebooker.serialization.serializers import PyMongoNotebookResultSerializer


logger = logging.getLogger(__name__)


class Serializer(Enum):
    PYMONGO = "PyMongoNotebookResultSerializer"


def serializer_kwargs_from_os_envs():
    return {
        "user": os.environ.get("MONGO_USER"),
        "password": os.environ.get("MONGO_PASSWORD"),
        "mongo_host": os.environ.get("MONGO_HOST"),
        "database_name": os.environ.get("DATABASE_NAME"),
        "result_collection_name": os.environ.get("RESULT_COLLECTION_NAME"),
    }


def get_serializer_from_cls(serializer_cls: str, **kwargs: dict) -> NotebookResultSerializer:
    if serializer_cls == Serializer.PYMONGO.value:
        return PyMongoNotebookResultSerializer(**kwargs)
    else:
        raise ValueError("Unspported serializer {}".format(serializer_cls))


def get_fresh_serializer() -> NotebookResultSerializer:
    serializer_cls = os.environ.get("NOTEBOOK_SERIALIZER", Serializer.PYMONGO.value)
    serializer_kwargs = serializer_kwargs_from_os_envs()
    return get_serializer_from_cls(serializer_cls, **serializer_kwargs)
