import os
from functools import reduce
from logging import getLogger
from typing import Dict, Optional, Union

from flask import g, current_app
from werkzeug.datastructures import ImmutableMultiDict

from notebooker.constants import python_template_dir
from notebooker.serialization.mongo import MongoResultSerializer
from notebooker.serialization.serialization import get_serializer_from_cls
from notebooker.utils.templates import _valid_dirname, _valid_filename, _gen_all_templates, _extract_category

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
    categorization = current_app.config.get("CATEGORIZATION", False)
    starting_point = starting_point or _get_python_template_dir()
    all_dirs = {}
    rootdir = starting_point.rstrip(os.sep)
    start = rootdir.rfind(os.sep) + 1

    for path, _, files in os.walk(rootdir):
        if not _valid_dirname(path):
            continue
        folders = path[start:].split(os.sep)
        subdir = {}
        parent = all_dirs

        for f in files:
            full_path = os.path.join(starting_point, *folders[1:], f)
            if _valid_filename(f):
                if categorization:
                    category = _extract_category(full_path)
                    if category:
                        parent.setdefault(rootdir.split(os.sep)[-1], {}).setdefault(category, {})[os.path.join(*folders[1:], f)] = None
                else:
                    subdir[os.path.join(*folders[1:], f)] = None

        for folder in folders[:-1]:
            if folder not in parent:
                parent[folder] = {}
            parent = parent[folder]
        if not categorization:
            parent[folders[-1]] = subdir

    if categorization:
        all_dirs = filter_for_code_files(all_dirs)
        path_to_category_name = {name: original_key for original_key, sub_dict in all_dirs.get(rootdir.split(os.sep)[-1], {}).items()
                                 for name, value in sub_dict.items() if value is None}
        current_app.config["PATH_TO_CATEGORY_DICT"] = path_to_category_name

    stripped = strip_extensions(all_dirs)
    logger.info("Stripped directory structure %s", stripped)
    return stripped.get(rootdir[start:], {})


def strip_extensions(d):
    def strip_extension(item):
        """Strips .py or .ipynb extension from a given item, if present."""
        for ext in ('.py', '.ipynb'):
            if item.endswith(ext):
                return item[:-len(ext)]
        return item

    """
    Recursively removes .ipynb and .py extensions from all keys and values in the dictionary.
    """

    def process_dict(sub_d):
        """
        Recursively processes each item in the dictionary to strip extensions from keys and values.
        """
        new_dict = {}
        for k, v in sub_d.items():
            new_key = strip_extension(k)
            if isinstance(v, dict):
                new_dict[new_key] = process_dict(v)  # Recursive call for sub-dictionaries
            elif isinstance(v, str):
                new_dict[new_key] = strip_extension(v)  # Strip extension from values if string
            else:
                new_dict[new_key] = v  # Copy other values directly
        return new_dict

    return process_dict(d)


def filter_for_code_files(d):
    """
    Recursively filters a dictionary to retain only items that are either
    .py or .ipynb files or directories leading to such files.
    """

    def has_code_files(sub_d):
        """
        Determines whether a dictionary or its nested dictionaries contain
        any .py or .ipynb files.
        """
        if not isinstance(sub_d, dict):
            return False
        for k, v in sub_d.items():
            if isinstance(v, dict) and has_code_files(v):
                return True
            if k.endswith(('.py', '.ipynb')):
                return True
        return False

    def filter_dict(sub_d):
        """
        Recursively filters the dictionary to retain only keys leading to .py or .ipynb files,
        or to dictionaries that do, direct or indirectly.
        """
        new_dict = {}
        for k, v in sub_d.items():
            if isinstance(v, dict):
                filtered_sub_d = filter_dict(v)
                if has_code_files(filtered_sub_d):  # Retain if leads to code files
                    new_dict[k] = filtered_sub_d
            elif k.endswith(('.py', '.ipynb')):
                new_dict[k] = v
        return new_dict

    filtered_dict = filter_dict(d)
    return strip_extensions(filtered_dict)


def all_templates_flattened():
    return list(_gen_all_templates(get_all_possible_templates(warn_on_local=False)))


def get_all_templates():
    if current_app.config["CATEGORIZATION"]:
        return get_all_possible_templates(warn_on_local=False)
    else:
        return all_templates_flattened()
