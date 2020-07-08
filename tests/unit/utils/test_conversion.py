import json
import os
import shutil
import tempfile

import mock
from click.testing import CliRunner

from notebooker import convert_to_py
from notebooker.utils import conversion
from notebooker.utils.caching import get_cache, set_cache
from notebooker.utils.conversion import convert_report_path_into_name, _output_ipynb_name
from notebooker.utils.filesystem import _cleanup_dirs

from tests.utils import setup_and_cleanup_notebooker_filesystem


@setup_and_cleanup_notebooker_filesystem
def test_generate_ipynb_from_py():
    python_dir = tempfile.mkdtemp()
    try:
        set_cache("latest_sha", "fake_sha_early")

        os.mkdir(python_dir + "/extra_path")
        with open(os.path.join(python_dir, "extra_path", "test_report.py"), "w") as f:
            f.write("#hello world\n")
        report_path = os.sep.join(["extra_path", "test_report"])
        with mock.patch("notebooker.utils.conversion._git_pull_templates") as pull:
            conversion.python_template_dir = lambda *a, **kw: python_dir
            pull.return_value = "fake_sha_early"
            conversion.generate_ipynb_from_py(python_dir, report_path)
            pull.return_value = "fake_sha_later"
            conversion.generate_ipynb_from_py(python_dir, report_path)
            conversion.generate_ipynb_from_py(python_dir, report_path)

        assert get_cache("latest_sha") == "fake_sha_later"
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
                conversion.generate_ipynb_from_py(python_dir, "extra_path/test_report")

        expected_ipynb_path = os.path.join(python_dir, "uuid", expected_filename)
        assert os.path.exists(expected_ipynb_path), f".ipynb at {expected_ipynb_path} was not generated as expected!"

        with mock.patch("notebooker.utils.conversion.uuid.uuid4") as uuid4:
            conversion.python_template_dir = lambda *a, **kw: python_dir
            conversion.NOTEBOOKER_DISABLE_GIT = True
            uuid4.return_value = "uuid_nogit"
            conversion.generate_ipynb_from_py(python_dir, "extra_path/test_report")

        expected_ipynb_path = os.path.join(python_dir, "uuid_nogit", expected_filename)
        assert os.path.exists(expected_ipynb_path), ".ipynb was not generated as expected!"

    finally:
        _cleanup_dirs()
        shutil.rmtree(python_dir)


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


@mock.patch("notebooker.utils.conversion.set_cache")
@mock.patch("notebooker.utils.conversion.get_cache")
@mock.patch("notebooker.utils.conversion._git_pull_templates")
@mock.patch("notebooker.utils.conversion.uuid.uuid4")
def test__get_output_path_hex(uuid4, pull, get_cache, set_cache):
    # No-git path
    conversion.python_template_dir = lambda *a, **kw: None
    uuid4.return_value = mock.sentinel.uuid4
    actual = conversion._get_output_path_hex()
    assert actual == str(mock.sentinel.uuid4)

    # Git path set new SHA
    conversion.python_template_dir = lambda *a, **kw: mock.sentinel.pydir
    conversion.NOTEBOOKER_DISABLE_GIT = False
    pull.return_value = mock.sentinel.newsha
    get_cache.return_value = mock.sentinel.newsha2
    actual = conversion._get_output_path_hex()
    assert actual == mock.sentinel.newsha2
    set_cache.assert_called_once_with("latest_sha", mock.sentinel.newsha)

    # Git path old SHA
    get_cache.return_value = None
    actual = conversion._get_output_path_hex()
    assert actual == "OLD"

    # Git path same SHA
    get_cache.return_value = pull.return_value = mock.sentinel.samesha
    set_cache.reset_mock()
    actual = conversion._get_output_path_hex()
    assert actual == mock.sentinel.samesha
    assert not set_cache.called
