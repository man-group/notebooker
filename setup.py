import os

from setuptools import find_packages, setup


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
        desc += "\n\n"
    return desc


setup(
    version=get_version(),
    packages=find_packages(exclude=["tests", "tests.*", "benchmarks"]),
    namespace_packages=["notebooker"],
    python_requires=">=3.6",
    zip_safe=False,
    include_package_data=True,
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    entry_points={
        "console_scripts": [
            "notebooker-cli = notebooker._entrypoints:base_notebooker",
            "notebooker_execute = notebooker.execute_notebook:docker_compose_entrypoint",
            "notebooker_template_sanity_check = notebooker.utils.template_testing:sanity_check",
            "notebooker_template_regression_test = notebooker.utils.template_testing:regression_test",
            "convert_ipynb_to_py = notebooker.convert_to_py:main",
        ]
    },
)
