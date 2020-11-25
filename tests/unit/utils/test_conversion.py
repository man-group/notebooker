import json
import os
import shutil
import tempfile

import mock
from click.testing import CliRunner

from notebooker import convert_to_py
from notebooker.utils import conversion
from notebooker.utils.caching import set_cache
from notebooker.utils.conversion import _output_ipynb_name


def test_generate_ipynb_from_py(setup_and_cleanup_notebooker_filesystem, webapp_config, flask_app):
    python_dir = webapp_config.PY_TEMPLATE_BASE_DIR
    with flask_app.app_context():
        set_cache("latest_sha", "fake_sha_early")

        os.mkdir(python_dir + "/extra_path")
        with open(os.path.join(python_dir, "extra_path", "test_report.py"), "w") as f:
            f.write("#hello world\n")
        report_path = os.sep.join(["extra_path", "test_report"])
        with mock.patch("notebooker.utils.conversion.git.repo.Repo") as repo:
            repo().commit().hexsha = "fake_sha_early"
            conversion.generate_ipynb_from_py(python_dir, report_path, False, python_dir)
            repo().commit().hexsha = "fake_sha_later"
            conversion.generate_ipynb_from_py(python_dir, report_path, False, python_dir)
            conversion.generate_ipynb_from_py(python_dir, report_path, False, python_dir)

        expected_filename = _output_ipynb_name(report_path)
        expected_ipynb_path = os.path.join(python_dir, "fake_sha_early", expected_filename)
        assert os.path.exists(expected_ipynb_path), f".ipynb at {expected_ipynb_path} was not generated as expected!"
        expected_ipynb_path = os.path.join(python_dir, "fake_sha_later", expected_filename)
        assert os.path.exists(expected_ipynb_path), ".ipynb was not generated as expected!"

        with mock.patch("notebooker.utils.conversion.uuid.uuid4") as uuid4:
            with mock.patch("notebooker.utils.conversion.pkg_resources.resource_filename") as resource_filename:
                conversion.python_template_dir = lambda *a, **kw: None
                uuid4.return_value = "uuid"
                resource_filename.return_value = python_dir + "/extra_path/test_report.py"
                conversion.generate_ipynb_from_py(python_dir, "extra_path/test_report", False, py_template_dir="")

        expected_ipynb_path = os.path.join(python_dir, "uuid", expected_filename)
        assert os.path.exists(expected_ipynb_path), f".ipynb at {expected_ipynb_path} was not generated as expected!"

        with mock.patch("notebooker.utils.conversion.uuid.uuid4") as uuid4:
            conversion.python_template_dir = lambda *a, **kw: python_dir
            conversion.NOTEBOOKER_DISABLE_GIT = True
            uuid4.return_value = "uuid_nogit"
            conversion.generate_ipynb_from_py(python_dir, "extra_path/test_report", True, py_template_dir=python_dir)

        expected_ipynb_path = os.path.join(python_dir, "uuid_nogit", expected_filename)
        assert os.path.exists(expected_ipynb_path), ".ipynb was not generated as expected!"


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
