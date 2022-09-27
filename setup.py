import os

from setuptools import setup


def get_version():
    # https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-version
    base_dir = os.path.abspath(os.path.dirname(__file__))
    version_file_loc = os.path.join(base_dir, ".", "notebooker", "version.py")
    version = {}
    with open(version_file_loc) as version_file:
        exec(version_file.read(), version)
    return version["__version__"]


def get_long_description():
    desc = ""
    for filename in ("README.md", "CHANGELOG.md"):
        with open(filename, "r", encoding="utf-8") as f:
            desc += f.read()
    return desc


setup(
    version=get_version(),
    long_description=get_long_description(),
    zip_safe=False,
    include_package_data=True,
)
