from logging import getLogger

import pytest

from notebooker.utils.conversion import generate_ipynb_from_py
from notebooker.utils.filesystem import get_template_dir
from notebooker.utils.templates import _get_parameters_cell_idx, _get_preview, template_name_to_notebook_node

from ..utils import _all_templates

logger = getLogger("template_sanity_check")


@pytest.mark.parametrize("template_name", _all_templates())
def test_conversion_doesnt_fail(template_name):
    # Test conversion to ipynb - this will throw if stuff goes wrong
    generate_ipynb_from_py(get_template_dir(), template_name, warn_on_local=False)


@pytest.mark.parametrize("template_name", _all_templates())
def test_template_has_parameters(template_name):
    generate_ipynb_from_py(get_template_dir(), template_name, warn_on_local=False)
    nb = template_name_to_notebook_node(template_name, warn_on_local=False)
    metadata_idx = _get_parameters_cell_idx(nb)
    assert metadata_idx is not None, 'Template {} does not have a "parameters"-tagged cell.'.format(template_name)


@pytest.mark.parametrize("template_name", _all_templates())
def test_template_can_generate_preview(template_name):
    preview = _get_preview(template_name, warn_on_local=False)
    # Previews in HTML are gigantic since they include all jupyter css and js.
    assert len(preview) > 1000, "Preview was not properly generated for {}".format(template_name)
