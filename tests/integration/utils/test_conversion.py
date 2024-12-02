import json
import os
import uuid

import mock
import pytest

from notebooker.utils import conversion
from notebooker.utils.caching import set_cache
from notebooker.utils.conversion import _output_ipynb_name


@pytest.mark.parametrize("file_type", ["py", "ipynb"])
def test_generate_ipynb_from_py(file_type, setup_and_cleanup_notebooker_filesystem, webapp_config, flask_app):
    python_dir = webapp_config.PY_TEMPLATE_BASE_DIR
    with flask_app.app_context():
        set_cache("latest_sha", "fake_sha_early")

        os.mkdir(python_dir / "extra_path")
        with open(os.path.join(python_dir, "extra_path", f"test_report.{file_type}"), "w") as f:
            if file_type == "py":
                f.write("#hello world\n")
            elif file_type == "ipynb":
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

        uuid_1 = uuid.UUID(int=12345)
        uuid_2 = uuid.UUID(int=67890)
        with mock.patch("notebooker.utils.conversion.uuid.uuid4") as uuid4:
            with mock.patch("notebooker.utils.conversion._template") as template:
                conversion.python_template_dir = lambda *a, **kw: None
                uuid4.return_value = uuid_1
                template.return_value = str(python_dir) + f"/extra_path/test_report.{file_type}"
                conversion.generate_ipynb_from_py(python_dir, "extra_path/test_report", False, py_template_dir="")

        expected_ipynb_path = os.path.join(python_dir, str(uuid_1), expected_filename)
        assert os.path.exists(expected_ipynb_path), f".ipynb at {expected_ipynb_path} was not generated as expected!"

        with mock.patch("notebooker.utils.conversion.uuid.uuid4") as uuid4:
            conversion.python_template_dir = lambda *a, **kw: python_dir
            conversion.NOTEBOOKER_DISABLE_GIT = True
            uuid4.return_value = uuid_2
            conversion.generate_ipynb_from_py(python_dir, "extra_path/test_report", True, py_template_dir=python_dir)

        expected_ipynb_path = os.path.join(python_dir, str(uuid_2), expected_filename)
        assert os.path.exists(expected_ipynb_path), ".ipynb was not generated as expected!"
