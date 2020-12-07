import os
from functools import reduce
from logging import getLogger
from typing import Dict, Optional, Union

from flask import g, current_app
from werkzeug.datastructures import ImmutableMultiDict

from notebooker.constants import python_template_dir
from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.serialization.serialization import get_serializer_from_cls
from notebooker.utils.templates import _valid_dirname, _valid_filename, _gen_all_templates

logger = getLogger(__name__)


def get_serializer() -> MongoResultSerializer:
    if not hasattr(g, "notebook_serializer"):
        config = current_app.config
        g.notebook_serializer = get_serializer_from_cls(config["SERIALIZER_CLS"], **config["SERIALIZER_CONFIG"])
    return g.notebook_serializer


def _params_from_request_args(request_args: ImmutableMultiDict) -> Dict:
    return {k: (v[0] if len(v) == 1 else v) for k, v in request_args.lists()}


def _get_python_template_dir() -> str:
    return python_template_dir(current_app.config["PY_TEMPLATE_BASE_DIR"], current_app.config["PY_TEMPLATE_SUBDIR"])


def get_all_possible_templates(warn_on_local=True):
    if _get_python_template_dir():
        all_checks = get_directory_structure()
    else:
        if warn_on_local:
            logger.warning("Fetching all possible checks from local repo. New updates will not be retrieved from git.")
        # Only import here because we don't actually want to import these if the app is working properly.
        from notebooker import notebook_templates_example

        all_checks = get_directory_structure(os.path.abspath(notebook_templates_example.__path__[0]))
    return all_checks


def get_directory_structure(starting_point: Optional[str] = None) -> Dict[str, Union[Dict, None]]:
    """
    Creates a nested dictionary that represents the folder structure of rootdir
    """
    starting_point = starting_point or _get_python_template_dir()
    all_dirs = {}
    rootdir = starting_point.rstrip(os.sep)
    start = rootdir.rfind(os.sep) + 1
    for path, dirs, files in os.walk(rootdir):
        if not _valid_dirname(path):
            continue
        folders = path[start:].split(os.sep)
        subdir = {os.sep.join(folders[1:] + [f.replace(".py", "")]): None for f in files if _valid_filename(f)}
        parent = reduce(dict.get, folders[:-1], all_dirs)
        parent[folders[-1]] = subdir
    return all_dirs[rootdir[start:]]


def _all_templates():
    templates = list(_gen_all_templates(get_all_possible_templates(warn_on_local=False)))
    return templates
