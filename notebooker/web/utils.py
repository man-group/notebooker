from typing import Dict

from flask import g
from werkzeug.datastructures import ImmutableMultiDict

from notebooker.serialization.mongo import NotebookResultSerializer
from notebooker.serialization.serialization import get_fresh_serializer


def get_serializer() -> NotebookResultSerializer:
    if not hasattr(g, "notebook_serializer"):
        g.notebook_serializer = get_fresh_serializer()
    return g.notebook_serializer


def _params_from_request_args(request_args: ImmutableMultiDict) -> Dict:
    return {k: (v[0] if len(v) == 1 else v) for k, v in request_args.lists()}
