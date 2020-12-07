import os

from setuptools import find_packages, setup


def get_version():
    # https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-version
    base_dir = os.path.abspath(os.path.dirname(__file__))
    version_file_loc = os.path.join(base_dir, ".", "notebooker", "_version.py")
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


# Note: pytest >= 4.1.0 is not compatible with pytest-cov < 2.6.1.
test_requirements = [
    "openpyxl",
    "pytest",
    "mock",
    "pytest-cov",
    "pytest-timeout",
    "pytest-xdist",
    "pytest-server-fixtures",
    "freezegun",
    "hypothesis>=3.83.2",
]

setup(
    name="notebooker",
    version=get_version(),
    author="Man Quant Technology",
    author_email="ManAlphaTech@man.com",
    description="Tool for parametrizing, executing, and displaying Jupyter Notebooks as reports.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    license="AGPLv3",
    url="https://github.com/man-group/notebooker",
    packages=find_packages(exclude=["tests", "tests.*", "benchmarks"]),
    namespace_packages=["notebooker"],
    setup_requires=["six", "numpy"],
    python_requires=">=3.5",
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        "gevent",
        "ipython",
        "pandas",
        "matplotlib",
        "pymongo",
        "papermill",
        "dataclasses",
        "nbconvert<6.0.0",  # Pin this because new template locations do not seem to work on OSX
        "nbformat",
        "jupytext>=1.2.0",
        "ipykernel",
        "stashy",
        "click>7.1.0",
        "python-dateutil",
        "flask",
        "requests",
        "retrying",
        "gitpython",
        "cachelib",
    ],
    extras_require={
        "prometheus": ["prometheus_client"],
        "test": test_requirements,
        "docs": [
            "sphinx<3.0.0",
            "numpydoc",
            "sphinxcontrib-httpdomain",
        ],  # Sphinx v3 doesn't play nicely with Flask, yet.
    },
    tests_require=test_requirements,
    entry_points={
        "console_scripts": [
            "notebooker-cli = notebooker._entrypoints:base_notebooker",
            "notebooker_execute = notebooker.execute_notebook:docker_compose_entrypoint",
            "notebooker_template_sanity_check = notebooker.utils.template_testing:sanity_check",
            "notebooker_template_regression_test = notebooker.utils.template_testing:regression_test",
            "convert_ipynb_to_py = notebooker.convert_to_py:main",
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Framework :: Flask",
        "Framework :: IPython",
        "Framework :: Jupyter",
        "Programming Language :: Python :: 3.6",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries",
    ],
)
