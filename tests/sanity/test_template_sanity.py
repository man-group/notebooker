from logging import getLogger

import pytest

from notebooker.utils.conversion import generate_ipynb_from_py
from notebooker.utils.templates import _get_parameters_cell_idx, _get_preview, template_name_to_notebook_node

from ..utils import all_templates

logger = getLogger("template_sanity_check")

x
@pytest.fixture(autouse=True)
def clean_file_cache(clean_file_cache):
    pass


@pytest.mark.parametrize("template_name", all_templates())
def test_conversion_doesnt_fail(template_name, template_dir):
    # Test conversion to ipynb - this will throw if stuff goes wrong
    generate_ipynb_from_py(
        template_dir, template_name, notebooker_disable_git=True, py_template_dir="", warn_on_local=False
    )


@pytest.mark.parametrize("template_name", all_templates())
def test_template_has_parameters(template_name, template_dir, flask_app):
    flask_app.config["PY_TEMPLATE_DIR"] = ""
    with flask_app.app_context():
        generate_ipynb_from_py(
            template_dir, template_name, notebooker_disable_git=True, py_template_dir="", warn_on_local=False
        )
        nb = template_name_to_notebook_node(
            template_name, notebooker_disable_git=True, py_template_dir="", warn_on_local=False
        )
        metadata_idx = _get_parameters_cell_idx(nb)
        assert metadata_idx is not None, 'Template {} does not have a "parameters"-tagged cell.'.format(template_name)


@pytest.mark.parametrize("template_name", all_templates())
def test_template_can_generate_preview(template_dir, template_name, flask_app):
    flask_app.config["PY_TEMPLATE_DIR"] = ""
    with flask_app.app_context():
        preview = _get_preview(template_name, notebooker_disable_git=True, py_template_dir="", warn_on_local=False)
        # Previews in HTML are gigantic since they include all jupyter css and js.
        assert len(preview) > 1000, "Preview was not properly generated for {}".format(template_name)
