import datetime
import uuid

import pytest

from notebooker.execute_notebook import _run_checks
from notebooker.utils.filesystem import _cleanup_dirs, get_output_dir, get_template_dir

from ..utils import _all_templates


@pytest.mark.parametrize("template_name", _all_templates())
def test_execution_of_templates(template_name):
    try:
        _run_checks(
            "job_id_{}".format(str(uuid.uuid4())[:6]),
            datetime.datetime.now(),
            template_name,
            template_name,
            get_output_dir(),
            get_template_dir(),
            {},
            generate_pdf_output=False,
        )
    finally:
        _cleanup_dirs()
