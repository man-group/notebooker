import logging

from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.settings import BaseConfig
from . import ALL_SERIALIZERS


logger = logging.getLogger(__name__)


def get_serializer_from_cls(serializer_cls: str, **kwargs: dict) -> MongoResultSerializer:
    serializer = ALL_SERIALIZERS.get(serializer_cls)
    if serializer is None:
        raise ValueError("Unsupported serializer {}".format(serializer_cls))
    logger.info(f"Initialising {serializer_cls} with args: {kwargs}")
    return serializer(**kwargs)


def get_serializer_from_flask_session() -> MongoResultSerializer:
    from flask import current_app  # TODO moveme?

    return get_serializer_from_cls(current_app.config["SERIALIZER_CLS"], **current_app.config["SERIALIZER_ARGS"])


def initialize_serializer_from_config(config: BaseConfig) -> MongoResultSerializer:
    return get_serializer_from_cls(config.SERIALIZER_CLS, **config.SERIALIZER_CONFIG)
