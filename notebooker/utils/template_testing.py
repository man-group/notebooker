import datetime
import os
import uuid
from contextlib import contextmanager
from logging import getLogger
from tempfile import TemporaryDirectory

import click

import notebooker.web.utils
from notebooker.web.app import create_app, setup_app
from notebooker.settings import WebappConfig
from notebooker.exceptions import NotebookRunException
from notebooker.execute_notebook import _run_checks
from notebooker.utils import filesystem, templates
from notebooker.utils.conversion import generate_ipynb_from_py

logger = getLogger(__name__)


@contextmanager
def setup_test(template_dir):
    try:
        with TemporaryDirectory() as tmpdir:
            app = create_app()
            web_config = WebappConfig()
            web_config.PY_TEMPLATE_BASE_DIR = template_dir
            web_config.CACHE_DIR = tmpdir
            web_config.DISABLE_SCHEDULER = True
            app = setup_app(app, web_config)
            with app.app_context():
                yield
    finally:
        filesystem._cleanup_dirs(web_config)


@click.command()
@click.option("--template-dir", default="notebook_templates")
def sanity_check(template_dir):
    logger.info(f"Starting sanity check in {template_dir}")
    with setup_test(template_dir):
        for template_name in notebooker.web.utils.all_templates_flattened():
            logger.info(f"========================[ Sanity checking {template_name} ]========================")
            # Test conversion to ipynb - this will throw if stuff goes wrong
            generate_ipynb_from_py(
                filesystem.get_template_dir(),
                template_name,
                notebooker_disable_git=True,
                py_template_dir=template_dir,
                warn_on_local=False,
            )

            # Test that each template has parameters as expected
            nb = templates.template_name_to_notebook_node(
                template_name, notebooker_disable_git=True, py_template_dir=template_dir, warn_on_local=False
            )
            param_idx = templates._get_parameters_cell_idx(nb)
            if param_idx is None:
                logger.warning(f'Template {template_name} does not have a "parameters"-tagged cell.')

            # Test that we can generate a preview from the template
            preview = templates._get_preview(
                template_name=template_name,
                notebooker_disable_git=True,
                py_template_dir=template_dir,
                warn_on_local=False,
            )
            # Previews in HTML are gigantic since they include all jupyter css and js.
            assert len(preview) > 1000, f"Preview was not properly generated for {template_name}"
            logger.info(f"========================[ {template_name} PASSED ]========================")


@click.command()
@click.option("--template-dir", default="notebook_templates")
def regression_test(template_dir):
    logger.info("Starting regression test")
    with setup_test(template_dir):
        attempted_templates, failed_templates = [], set()
        for template_name in notebooker.web.utils.all_templates_flattened():
            logger.info(f"============================[ Testing {template_name} ]============================")
            try:
                attempted_templates.append(template_name)
                _run_checks(
                    "job_id_{}".format(str(uuid.uuid4())[:6]),
                    datetime.datetime.now(),
                    template_name,
                    template_name,
                    filesystem.get_output_dir(),
                    filesystem.get_template_dir(),
                    {},
                    generate_pdf_output=False,
                    py_template_base_dir=template_dir,
                )
                logger.info("===============================[ SUCCESS ]==============================")
            except Exception:
                failed_templates.add(template_name)
                logger.info("===============================[ FAILED ]===============================")
                logger.exception(f"Failed to execute template {template_name}")

        for template in attempted_templates:
            logger.info("{}: {}".format(template, "FAILED" if template in failed_templates else "PASSED"))
        if len(failed_templates) > 0:
            raise NotebookRunException(
                "The following templates failed to execute with no parameters:\n{}".format("\n".join(failed_templates))
            )


if __name__ == "__main__":
    sanity_check()
    regression_test()
