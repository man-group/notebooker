import logging

from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.settings import BaseConfig
from . import ALL_SERIALIZERS


logger = logging.getLogger(__name__)


def get_serializer_from_cls(serializer_cls: str, **kwargs: dict) -> MongoResultSerializer:
    serializer = ALL_SERIALIZERS.get(serializer_cls)
    if serializer is None:
        raise ValueError(f"Unsupported serializer {serializer_cls}. Supported: {list(ALL_SERIALIZERS)}")
    kw = {k.lower(): v for (k, v) in kwargs.items()}
    logger.info(f"Initialising {serializer_cls} with args: {kw}")
    return serializer(**kw)


def get_serializer_from_flask_session() -> MongoResultSerializer:
    from flask import current_app  # TODO moveme?

    return get_serializer_from_cls(current_app.config["SERIALIZER_CLS"], **current_app.config["SERIALIZER_ARGS"])


def initialize_serializer_from_config(config: BaseConfig) -> MongoResultSerializer:
    return get_serializer_from_cls(config.SERIALIZER_CLS, **config.SERIALIZER_CONFIG)
