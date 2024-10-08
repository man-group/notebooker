import os
import pytest
import shutil
import tempfile

from flask import Flask

from notebooker.utils.filesystem import mkdir_p
from notebooker.utils.templates import _valid_dirname
from notebooker.web.utils import get_directory_structure


@pytest.fixture
def app_context():
    app = Flask(__name__)
    # Configure your app for testing here
    ctx = app.app_context()
    ctx.push()  # Pushes the application context

    yield app  # This makes the app available to the test functions

    ctx.pop()  # Removes the application context after test completion


@pytest.mark.parametrize(
    "input_dirname, expected_result",
    [
        ("./my_directory", True),
        ("../hello_world/a/b/c/", True),
        (".git/blah", False),
        ("../.git/hello/world", False),
        ("normal/path/to/something", True),
        ("/absolute/path/.git", False),
        ("/absolute/path/git", True),
    ],
)
def test_valid_dirnames(input_dirname, expected_result):
    assert _valid_dirname(input_dirname) is expected_result


def test_get_directory_structure(app_context):
    temp_dir = tempfile.mkdtemp()
    try:
        paths = [
            "hello.py",
            "goodbye.py",
            "depth/1.py",
            "this/is/very/deep.py",
            "depth/2.py",
            "this/is/deep.py",
            "this/report.py",
            "hello_again.ipynb",
            "depth/3.ipynb",
            ".hidden/4.ipynb",
            ".hidden/visible/5.ipynb",
            ".hidden/.more-hidden/6.ipynb",
            "./visible/7.ipynb",
            "this/is/../is/8.ipynb",
        ]
        for path in paths:
            abspath = os.path.join(temp_dir, path)
            if "/" in path:
                mkdir_p(os.path.dirname(abspath))
            with open(abspath, "w") as f:
                f.write("#hello")
        expected_structure = {
            "hello": None,
            "goodbye": None,
            "depth": {"depth/1": None, "depth/2": None, "depth/3": None},
            "this": {
                "this/report": None,
                "is": {"this/is/8": None, "this/is/deep": None, "very": {"this/is/very/deep": None}},
            },
            "hello_again": None,
            "visible": {"visible/7": None},
        }

        assert get_directory_structure(temp_dir) == expected_structure
    finally:
        shutil.rmtree(temp_dir)


def test_get_directory_structure_categorized(app_context):
    app_context.config["CATEGORIZATION"] = True
    temp_dir = tempfile.mkdtemp()
    try:
        expected_structure = {
            "cat1": {"cat1_nb": None, "subdir/cat1_nb_subdir": None},
            "cat2": {"cat2_nb": None, "subdir/cat2_nb_subdir": None},
        }

        templates_path = os.path.join(os.path.dirname(__file__), "templates")
        actual_structure = get_directory_structure(templates_path)
        assert actual_structure == expected_structure
    finally:
        shutil.rmtree(temp_dir)
