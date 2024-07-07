import datetime
import uuid
import os
import pytest
from notebooker.execute_notebook import _run_checks
from notebooker import notebook_templates_example
from ..utils import templates_with_local_context, templates_without_local_context


@pytest.fixture(scope="module")
def py_template_base_dir():
    return os.path.abspath(notebook_templates_example.__path__[0])


@pytest.mark.parametrize("template_name", templates_without_local_context())
def test_execution_of_templates(template_name, template_dir, output_dir, flask_app, py_template_base_dir):
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
            generate_pdf_output=False,
        )


@pytest.mark.parametrize("template_name", templates_with_local_context())
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
