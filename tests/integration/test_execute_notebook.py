from __future__ import unicode_literals

import mock
import os

from click.testing import CliRunner
from nbformat import NotebookNode
from nbformat import __version__ as nbv

from notebooker import execute_notebook
from notebooker.constants import NotebookResultComplete
from notebooker.serialization.serializers import PyMongoNotebookResultSerializer
from notebooker.web.app import setup_env_vars


def mock_nb_execute(input_path, output_path, **kw):
    with open(output_path, "w") as f:
        f.write('{"cells": [], "metadata": {}}')


def test_main(mongo_host):
    with mock.patch("notebooker.execute_notebook.pm.execute_notebook") as exec_nb, mock.patch(
        "notebooker.utils.conversion.jupytext.read"
    ) as read_nb, mock.patch("notebooker.utils.conversion.PDFExporter") as pdf_exporter:
        pdf_contents = b"This is a PDF."
        pdf_exporter().from_notebook_node.return_value = (pdf_contents, None)
        versions = nbv.split(".")
        major, minor = int(versions[0]), int(versions[1])
        if major >= 5:
            major, minor = 4, 4
        read_nb.return_value = NotebookNode({"cells": [], "metadata": {}, "nbformat": major, "nbformat_minor": minor})
        exec_nb.side_effect = mock_nb_execute
        job_id = "ttttteeeesssstttt"
        runner = CliRunner()
        # usually the parent process calls this and sets up the environment, then also explicitly passes
        # values on the CLI
        setup_env_vars()
        cli_result = runner.invoke(
            execute_notebook.main, ["--report-name", "test_report", "--mongo-host", mongo_host, "--job-id", job_id]
        )
        assert cli_result.exit_code == 0
        serializer = PyMongoNotebookResultSerializer(
            mongo_host=mongo_host,
            database_name=os.environ["DATABASE_NAME"],
            result_collection_name=os.environ["RESULT_COLLECTION_NAME"],
        )
        result = serializer.get_check_result(job_id)
        assert isinstance(result, NotebookResultComplete), "Result is not instance of {}, it is {}".format(
            NotebookResultComplete, type(result)
        )
        assert result.raw_ipynb_json
        assert result.pdf == pdf_contents
