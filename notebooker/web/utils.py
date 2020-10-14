from typing import Dict

from flask import g, current_app
from werkzeug.datastructures import ImmutableMultiDict

from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.serialization.serialization import get_serializer_from_cls


def get_serializer() -> MongoResultSerializer:
    if not hasattr(g, "notebook_serializer"):
        config = current_app.config
        g.notebook_serializer = get_serializer_from_cls(config["SERIALIZER_CLS"], **config["SERIALIZER_CONFIG"])
    return g.notebook_serializer


def _params_from_request_args(request_args: ImmutableMultiDict) -> Dict:
    return {k: (v[0] if len(v) == 1 else v) for k, v in request_args.lists()}
