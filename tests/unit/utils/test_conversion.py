import json
import os
import shutil
import tempfile
import uuid

import pytest
import mock
from click.testing import CliRunner

from notebooker import convert_to_py
from notebooker.utils import conversion
from notebooker.utils.caching import set_cache
from notebooker.utils.conversion import _output_ipynb_name


def test_generate_py_from_ipynb():
    ipynb_dir = tempfile.mkdtemp()
    py_dir = tempfile.mkdtemp()
    try:
        for fname in [os.path.join(ipynb_dir, x + ".ipynb") for x in list("abcd")]:
            with open(fname, "w") as f:
                f.write(
                    json.dumps(
                        {
                            "cells": [
                                {
                                    "cell_type": "code",
                                    "execution_count": 2,
                                    "metadata": {},
                                    "outputs": [],
                                    "source": ["import datetime"],
                                }
                            ],
                            "metadata": {},
                            "nbformat": 4,
                            "nbformat_minor": 2,
                        }
                    )
                )

        runner = CliRunner()
        result = runner.invoke(
            convert_to_py.main,
            [
                os.path.join(ipynb_dir, "a.ipynb"),
                os.path.join(ipynb_dir, "b.ipynb"),
                os.path.join(ipynb_dir, "c.ipynb"),
                os.path.join(ipynb_dir, "d.ipynb"),
                "--output-dir",
                py_dir,
            ],
        )
        if result.exception:
            raise result.exception
        assert result.exit_code == 0

        for fname in [os.path.join(py_dir, x + ".py") for x in list("abcd")]:
            with open(fname, "r") as f:
                result = f.read()
            assert "import datetime" in result
            assert result.startswith("# ---\n# jupyter:")
    finally:
        shutil.rmtree(ipynb_dir)
        shutil.rmtree(py_dir)
