import os
import uuid

import click

from notebooker._version import __version__
from notebooker.constants import DEFAULT_SERIALIZER
from notebooker.execute_notebook import execute_notebook_entrypoint
from notebooker.serialization import SERIALIZER_TO_CLI_OPTIONS
from notebooker.settings import BaseConfig, WebappConfig
from notebooker.snapshot import snap_latest_successful_notebooks
from notebooker.web.app import main


class NotebookerEntrypoint(click.Group):
    def parse_args(self, ctx, args):
        try:
            serializer_arg = args.index("--serializer-cls")
            serializer = args[serializer_arg + 1]
        except ValueError:
            serializer = DEFAULT_SERIALIZER
        self.params += SERIALIZER_TO_CLI_OPTIONS[serializer].params

        return super().parse_args(ctx, args)


pass_config = click.make_pass_decorator(BaseConfig)


def filesystem_default_value(dirname):
    return os.path.join(os.path.expanduser("~"), ".notebooker", dirname, str(uuid.uuid4()))


@click.group(cls=NotebookerEntrypoint)
@click.version_option(__version__, prog_name="Notebooker")
@click.option("--notebook-kernel-name", default=None, help="The name of the kernel which is running our notebook code.")
@click.option(
    "--output-base-dir",
    default=filesystem_default_value("output"),
    help="The base directory to which we will save our notebook output temporarily. Required by Papermill.",
)
@click.option(
    "--template-base-dir",
    default=filesystem_default_value("templates"),
    help="The base directory to which we will save our notebook templates which have been converted "
    "from .py to .ipynb.",
)
@click.option(
    "--py-template-base-dir",
    default=None,
    help="The base directory of the git repository which holds the notebook templates as .py files. "
    "If not specified, this will default to the sample directory within notebooker.",
)
@click.option(
    "--py-template-subdir",
    default=None,
    help="The subdirectory of the git repository which contains only notebook templates.",
)
@click.option(
    "--notebooker-disable-git",
    default=False,
    is_flag=True,
    help="If selected, notebooker will not try to pull the latest version of python templates from git.",
)
@click.option(
    "--serializer-cls",
    default=DEFAULT_SERIALIZER,
    help="The serializer class through which we will save the notebook result.",
)
@click.pass_context
def base_notebooker(
    ctx,
    notebook_kernel_name,
    output_base_dir,
    template_base_dir,
    py_template_base_dir,
    py_template_subdir,
    notebooker_disable_git,
    serializer_cls,
    **serializer_args,
):
    config = BaseConfig(
        SERIALIZER_CLS=serializer_cls,
        SERIALIZER_CONFIG=serializer_args,
        NOTEBOOK_KERNEL_NAME=notebook_kernel_name,
        OUTPUT_DIR=output_base_dir,
        TEMPLATE_DIR=template_base_dir,
        PY_TEMPLATE_BASE_DIR=py_template_base_dir,
        PY_TEMPLATE_SUBDIR=py_template_subdir,
        NOTEBOOKER_DISABLE_GIT=notebooker_disable_git,
    )
    ctx.obj = config


@base_notebooker.command()
@click.option("--port", default=11828)
@click.option("--logging-level", default="INFO")
@click.option("--debug", default=False)
@click.option("--base-cache-dir", default=filesystem_default_value("webcache"))
@pass_config
def start_webapp(config: BaseConfig, port, logging_level, debug, base_cache_dir):
    web_config = WebappConfig.copy_existing(config)
    web_config.PORT = port
    web_config.LOGGING_LEVEL = logging_level
    web_config.DEBUG = debug
    web_config.CACHE_DIR = base_cache_dir
    return main(web_config)


@base_notebooker.command()
@click.option("--report-name", help="The name of the template to execute, relative to the template directory.")
@click.option(
    "--overrides-as-json", default="{}", help="The parameters to inject into the notebook template, in JSON format."
)
@click.option(
    "--iterate-override-values-of",
    default="",
    help="For the key/values in the overrides, set this to the value of one of the keys to run reports for "
    "each of its values.",
)
@click.option("--report-title", default="", help="A custom title for this notebook. The default is the report_name.")
@click.option("--n-retries", default=3, help="The number of times to retry when executing this notebook.")
@click.option(
    "--job-id",
    default=str(uuid.uuid4()),
    help="The unique job ID for this notebook. Can be non-unique, but note that you will overwrite history.",
)
@click.option("--mailto", default="", help="A comma-separated list of email addresses which will receive results.")
@click.option(
    "--error-mailto",
    default="",
    help="A comma-separated list of email addresses which will receive errors. Deafults to --mailto argument."
)
@click.option("--email-subject", default="", help="The subject of the email sent on a successful result.")
@click.option("--pdf-output/--no-pdf-output", default=True, help="Whether we generate PDF output or not.")
@click.option("--hide-code/--show-code", default=False, help="Hide code from email and PDF output.")
@click.option(
    "--prepare-notebook-only",
    is_flag=True,
    help='Used for debugging and testing. Whether to actually execute the notebook or just "prepare" it.',
)
@pass_config
def execute_notebook(
    config: BaseConfig,
    report_name,
    overrides_as_json,
    iterate_override_values_of,
    report_title,
    n_retries,
    job_id,
    mailto,
    error_mailto,
    email_subject,
    pdf_output,
    hide_code,
    prepare_notebook_only,
):
    if report_name is None:
        raise ValueError("Error! Please provide a --report-name.")
    return execute_notebook_entrypoint(
        config,
        report_name,
        overrides_as_json,
        iterate_override_values_of,
        report_title,
        n_retries,
        job_id,
        mailto,
        error_mailto,
        email_subject,
        pdf_output,
        hide_code,
        prepare_notebook_only,
    )


@base_notebooker.command()
@click.option(
    "--report-name", required=True, help="The name of the template to retrieve, relative to the template directory."
)
@pass_config
def snapshot_latest_successful_notebooks(config: BaseConfig, report_name):
    snap_latest_successful_notebooks(config, report_name)


if __name__ == "__main__":
    base_notebooker()
