import os
import shutil
import tempfile

from notebooker.utils.filesystem import mkdir_p
from notebooker.web.utils import get_directory_structure


def test_get_directory_structure():
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
            "this": {"this/report": None, "is": {"this/is/deep": None, "very": {"this/is/very/deep": None}}},
            "hello_again": None,
        }

        assert get_directory_structure(temp_dir) == expected_structure
    finally:
        shutil.rmtree(temp_dir)
