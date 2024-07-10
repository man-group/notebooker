import datetime
import os
import uuid

import pytest

from notebooker.execute_notebook import _run_checks


@pytest.fixture(scope="module")
def py_template_base_dir():
    import tests.regression.local_context as local_context
    return os.path.abspath(local_context.__path__[0])

def all_templates():
    return ["local_read", "local_import"]

@pytest.mark.parametrize("template_name", all_templates())
def test_execution_of_templates_with_local_context(
    template_name, template_dir, output_dir, flask_app, py_template_base_dir
):
    with flask_app.app_context():
        _run_checks(
            "job_id_{}".format(str(uuid.uuid4())[:6]),
            datetime.datetime.now(),
            template_name,
            template_name,
            output_dir,
            template_dir,
            {},
            py_template_base_dir=py_template_base_dir,
            execute_at_origin=True,
            generate_pdf_output=False,
        )
