import datetime
import os
import uuid
from logging import getLogger

import click

import notebooker.web.utils
from notebooker.exceptions import NotebookRunException
from notebooker.execute_notebook import _run_checks
from notebooker.utils import filesystem, templates
from notebooker.utils.conversion import generate_ipynb_from_py

logger = getLogger(__name__)


@click.command()
@click.option("--template-dir", default="notebook_templates")
def sanity_check(template_dir):
    logger.info("Starting sanity check")
    try:
        for template_name in notebooker.web.utils._all_templates():
            logger.info("========================[ Sanity checking {} ]========================".format(template_name))
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
                logger.warning('Template {} does not have a "parameters"-tagged cell.'.format(template_name))

            # Test that we can generate a preview from the template
            preview = templates._get_preview(template_name, warn_on_local=False)
            # Previews in HTML are gigantic since they include all jupyter css and js.
            assert len(preview) > 1000, "Preview was not properly generated for {}".format(template_name)
            logger.info("========================[ {} PASSED ]========================".format(template_name))
    finally:
        filesystem._cleanup_dirs()


@click.command()
@click.option("--template-dir", default="notebook_templates")
def regression_test(template_dir):
    logger.info("Starting regression test")
    try:
        attempted_templates, failed_templates = [], set()
        for template_name in notebooker.web.utils._all_templates():
            logger.info("============================[ Testing {} ]============================".format(template_name))
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
                )
                logger.info("===============================[ SUCCESS ]==============================")
            except Exception:
                failed_templates.add(template_name)
                logger.info("===============================[ FAILED ]===============================")
                logger.exception("Failed to execute template {}".format(template_name))

        for template in attempted_templates:
            logger.info("{}: {}".format(template, "FAILED" if template in failed_templates else "PASSED"))
        if len(failed_templates) > 0:
            raise NotebookRunException(
                "The following templates failed to execute with no parameters:\n{}".format("\n".join(failed_templates))
            )
    finally:
        filesystem._cleanup_dirs()


if __name__ == "__main__":
    sanity_check()
    regression_test()
