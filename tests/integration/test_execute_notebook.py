from __future__ import unicode_literals

import mock
import pytest
from click.testing import CliRunner
from nbformat import NotebookNode
from nbformat import __version__ as nbv

from notebooker._entrypoints import base_notebooker
from notebooker.constants import NotebookResultComplete, DEFAULT_SERIALIZER
from notebooker.serializers.pymongo import PyMongoResultSerializer


def mock_nb_execute(input_path, output_path, **kw):
    with open(output_path, "w") as f:
        f.write('{"cells": [], "metadata": {}}')


def test_main(mongo_host, setup_and_cleanup_notebooker_filesystem, webapp_config):
    with mock.patch("notebooker.utils.conversion.PDFExporter") as pdf_exporter:
        pdf_contents = b"This is a PDF."
        pdf_exporter().from_notebook_node.return_value = (pdf_contents, None)
        versions = nbv.split(".")
        major, minor = int(versions[0]), int(versions[1])
        if major >= 5:
            major, minor = 4, 4
        # read_nb.return_value = NotebookNode({"cells": [], "metadata": {}, "nbformat": major, "nbformat_minor": minor})
        job_id = "ttttteeeesssstttt"
        runner = CliRunner()
        cli_result = runner.invoke(
            base_notebooker,
            [
                "--serializer-cls",
                DEFAULT_SERIALIZER,
                "--py-template-base-dir",
                webapp_config.PY_TEMPLATE_BASE_DIR,
                "--py-template-subdir",
                webapp_config.PY_TEMPLATE_SUBDIR,
                "--output-base-dir",
                webapp_config.OUTPUT_DIR,
                "--template-base-dir",
                webapp_config.TEMPLATE_DIR,
                "--serializer-cls",
                webapp_config.SERIALIZER_CLS,
                "--mongo-host",
                webapp_config.SERIALIZER_CONFIG["mongo_host"],
                "--database-name",
                webapp_config.SERIALIZER_CONFIG["database_name"],
                "--result-collection-name",
                webapp_config.SERIALIZER_CONFIG["result_collection_name"],
                "execute-notebook",
                "--report-name",
                "fake/py_report",
                "--job-id",
                job_id,
            ],
        )
        if cli_result.exception:
            raise cli_result.exception
        assert not cli_result.exception, cli_result.output
        assert cli_result.exit_code == 0
        serializer = PyMongoResultSerializer(
            mongo_host=mongo_host, database_name="notebooker", result_collection_name="NOTEBOOK_OUTPUT"
        )
        result = serializer.get_check_result(job_id)
        assert isinstance(result, NotebookResultComplete), "Result is not instance of {}, it is {}".format(
            NotebookResultComplete, type(result)
        )
        assert result.raw_ipynb_json
        assert result.pdf == pdf_contents


@pytest.mark.parametrize(
    ("cli_args", "expected_mailto", "expected_from"),
    [
        (
            ["--report-name", "crashyreport", "--mailto", "happy@email", "--mailfrom", "notebooker@example.com"],
            None,
            "notebooker@example.com",
        ),
        (
            [
                "--report-name",
                "crashyreport",
                "--mailto",
                "happy@email",
                "--error-mailto",
                "sad@email",
                "--mailfrom",
                "notebooker@example.com",
            ],
            "sad@email",
            "notebooker@example.com",
        ),
        (
            ["--report-name", "crashyreport", "--error-mailto", "sad@email", "--mailfrom", "notebooker@example.com"],
            "sad@email",
            "notebooker@example.com",
        ),
    ],
)
def test_erroring_notebook_with_emails(mongo_host, cli_args, expected_mailto, expected_from):
    with mock.patch("notebooker.execute_notebook.pm.execute_notebook") as exec_nb, mock.patch(
        "notebooker.utils.conversion.jupytext.read"
    ) as read_nb, mock.patch("notebooker.utils.notebook_execution._send_email") as send_email:
        exec_nb.side_effect = Exception()
        versions = nbv.split(".")
        major, minor = int(versions[0]), int(versions[1])
        if major >= 5:
            major, minor = 4, 4
        read_nb.return_value = NotebookNode({"cells": [], "metadata": {}, "nbformat": major, "nbformat_minor": minor})
        job_id = "ttttteeeesssstttt"
        runner = CliRunner()
        cli_result = runner.invoke(
            base_notebooker,
            ["--serializer-cls", DEFAULT_SERIALIZER, "--mongo-host", mongo_host, "execute-notebook", "--job-id", job_id]
            + cli_args,
        )
        if expected_mailto is None:
            assert len(send_email.call_args_list) == 0
        else:
            mailfrom = send_email.call_args_list[0][1]["from_email"]
            mailto = send_email.call_args_list[0][1]["to_email"]
            assert mailto == expected_mailto
            assert mailfrom == expected_from
