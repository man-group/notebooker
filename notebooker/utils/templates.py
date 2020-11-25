from logging import getLogger
from typing import Optional

import nbformat
import pkg_resources
from nbconvert import HTMLExporter
from traitlets.config import Config

from notebooker.utils.caching import get_cache, set_cache
from notebooker.utils.conversion import generate_ipynb_from_py
from notebooker.utils.filesystem import get_template_dir

logger = getLogger(__name__)


def _valid_dirname(d):
    return "__init__" not in d and "__pycache__" not in d


def _valid_filename(f):
    return f.endswith(".py") and "__init__" not in f and "__pycache__" not in f


def _get_parameters_cell_idx(notebook: nbformat.NotebookNode) -> Optional[int]:
    for idx, cell in enumerate(notebook["cells"]):
        tags = cell.get("metadata", {}).get("tags", [])
        if "parameters" in tags:
            return idx
    return None


def template_name_to_notebook_node(
    template_name: str, notebooker_disable_git: bool, py_template_dir: str, warn_on_local: Optional[bool] = True
) -> nbformat.NotebookNode:
    path = generate_ipynb_from_py(
        get_template_dir(), template_name, notebooker_disable_git, py_template_dir, warn_on_local=warn_on_local
    )
    nb = nbformat.read(path, as_version=nbformat.v4.nbformat)
    return nb


def _get_preview(
    template_name: str, notebooker_disable_git: bool, py_template_dir: str, warn_on_local: Optional[bool] = True
) -> str:
    """ Returns an HTML render of a report template, with parameters highlighted. """
    cached = get_cache(("preview", template_name))
    if cached:
        logger.info("Getting %s preview from cache.", template_name)
        return cached
    nb = template_name_to_notebook_node(
        template_name, notebooker_disable_git, py_template_dir, warn_on_local=warn_on_local
    )
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
