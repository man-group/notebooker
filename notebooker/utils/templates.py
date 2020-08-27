import os
from functools import reduce
from logging import getLogger
from typing import Dict, Optional, Union

import nbformat
import pkg_resources
from nbconvert import HTMLExporter
from traitlets.config import Config

from notebooker.constants import python_template_dir
from notebooker.utils.caching import get_cache, set_cache
from notebooker.utils.conversion import generate_ipynb_from_py
from notebooker.utils.filesystem import get_template_dir

logger = getLogger(__name__)


def _valid_dirname(d):
    return "__init__" not in d and "__pycache__" not in d


def _valid_filename(f):
    return f.endswith(".py") and "__init__" not in f and "__pycache__" not in f


def get_directory_structure(starting_point: Optional[str] = None) -> Dict[str, Union[Dict, None]]:
    """
    Creates a nested dictionary that represents the folder structure of rootdir
    """
    starting_point = starting_point or python_template_dir()
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


def get_all_possible_templates(warn_on_local=True):
    if python_template_dir():
        all_checks = get_directory_structure()
    else:
        if warn_on_local:
            logger.warning("Fetching all possible checks from local repo. New updates will not be retrieved from git.")
        # Only import here because we don't actually want to import these if the app is working properly.
        from .. import notebook_templates_example

        all_checks = get_directory_structure(os.path.abspath(notebook_templates_example.__path__[0]))
    return all_checks


def _get_parameters_cell_idx(notebook: nbformat.NotebookNode) -> Optional[int]:
    for idx, cell in enumerate(notebook["cells"]):
        tags = cell.get("metadata", {}).get("tags", [])
        if "parameters" in tags:
            return idx
    return None


def template_name_to_notebook_node(template_name: str, warn_on_local: Optional[bool] = True) -> nbformat.NotebookNode:
    path = generate_ipynb_from_py(get_template_dir(), template_name, warn_on_local=warn_on_local)
    nb = nbformat.read(path, as_version=nbformat.v4.nbformat)
    return nb


def _get_preview(template_name: str, warn_on_local: Optional[bool] = True) -> str:
    """ Returns an HTML render of a report template, with parameters highlighted. """
    cached = get_cache(("preview", template_name))
    if cached:
        logger.info("Getting %s preview from cache.", template_name)
        return cached
    nb = template_name_to_notebook_node(template_name, warn_on_local=warn_on_local)
    parameters_idx = _get_parameters_cell_idx(nb)
    conf = Config()
    if parameters_idx is not None:
        # Use this template to highlight the cell with parameters
        conf.HTMLExporter.template_file = pkg_resources.resource_filename(
            __name__, "../nbtemplates/notebook_preview.tpl"
        )
    exporter = HTMLExporter(config=conf)
    html, _ = exporter.from_notebook_node(nb) if nb["cells"] else ("", "")
    set_cache(("preview", template_name), html, timeout=30)
    return html


def _gen_all_templates(template_dict):
    for template_name, children in template_dict.items():
        if children:
            for x in _gen_all_templates(children):  # Replace with "yield from" when we have py3
                yield x
        else:
            yield template_name


def _all_templates():
    templates = list(_gen_all_templates(get_all_possible_templates(warn_on_local=False)))
    return templates
