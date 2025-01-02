import os

import pytest
from pytest_server_fixtures import CONFIG
from pytest_server_fixtures.mongo import MongoTestServer
from pytest_fixture_config import yield_requires_config

from notebooker.constants import DEFAULT_DATABASE_NAME, DEFAULT_RESULT_COLLECTION_NAME, DEFAULT_SERIALIZER
from notebooker.settings import WebappConfig
from notebooker.utils import caching
from notebooker.utils.filesystem import initialise_base_dirs, _cleanup_dirs
from notebooker.web.app import create_app, setup_app


class MongoTestServerWithPath(MongoTestServer):
    @property
    def env(self):
        return {"PATH": os.environ["PATH"]}


def _mongo_server():
    """This does the actual work - there are several versions of this used
    with different scopes.
    """
    test_server = MongoTestServerWithPath()
    try:
        test_server.start()
        yield test_server
    finally:
        test_server.teardown()


@pytest.yield_fixture(scope="function")
@yield_requires_config(CONFIG, ["mongo_bin"])
def mongo_server():
    """Function-scoped MongoDB server started in a local thread.
    This also provides a temp workspace.
    We tear down, and cleanup mongos at the end of the test.

    For completeness, we tidy up any outstanding mongo temp directories
    at the start and end of each test session

    Attributes
    ----------
    api (`pymongo.MongoClient`)  : PyMongo Client API connected to this server
    .. also inherits all attributes from the `workspace` fixture
    """
    for server in _mongo_server():
        yield server


@pytest.fixture
def bson_library(mongo_server, test_db_name, test_lib_name):
    return mongo_server.api[test_db_name][test_lib_name]


@pytest.fixture
def mongo_host(mongo_server):
    return f"{mongo_server.hostname}:{mongo_server.port}"


@pytest.fixture
def test_db_name():
    return DEFAULT_DATABASE_NAME


@pytest.fixture
def test_lib_name():
    return DEFAULT_RESULT_COLLECTION_NAME


@pytest.fixture
def template_dir(workspace):
    return workspace.workspace


@pytest.fixture
def output_dir(workspace):
    return workspace.workspace


@pytest.fixture
def cache_dir(workspace):
    return workspace.workspace


@pytest.fixture
def py_template_dir(workspace):
    return workspace.workspace


def safe_cache_clear():
    if caching.cache is not None:
        try:
            caching.cache.clear()
        except FileNotFoundError:
            pass


@pytest.fixture
def clean_file_cache(monkeypatch, workspace):
    """Set up cache environment."""
    safe_cache_clear()
    monkeypatch.setenv("CACHE_DIR", str(workspace.workspace))
    yield
    # purge the cache
    safe_cache_clear()
    caching.cache = None


@pytest.fixture()
def webapp_config(mongo_host, test_db_name, test_lib_name, template_dir, cache_dir, output_dir, workspace):
    return WebappConfig(
        CACHE_DIR=cache_dir,
        OUTPUT_DIR=output_dir,
        TEMPLATE_DIR=template_dir,
        DISABLE_SCHEDULER=False,
        SERIALIZER_CLS=DEFAULT_SERIALIZER,
        SERIALIZER_CONFIG={
            "mongo_host": mongo_host,
            "database_name": test_db_name,
            "result_collection_name": test_lib_name,
        },
        PY_TEMPLATE_BASE_DIR=workspace.workspace,
        PY_TEMPLATE_SUBDIR="templates",
    )


@pytest.fixture()
def webapp_config_readonly(webapp_config):
    webapp_config.READONLY_MODE = True
    return webapp_config


@pytest.fixture
def flask_app(webapp_config):
    flask_app = create_app(webapp_config)
    flask_app = setup_app(flask_app, webapp_config)
    flask_app.config["DEBUG"] = True
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def flask_app_readonly(webapp_config_readonly):
    flask_app = create_app(webapp_config_readonly)
    flask_app = setup_app(flask_app, webapp_config_readonly)
    flask_app.config["DEBUG"] = True
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def setup_and_cleanup_notebooker_filesystem(webapp_config, setup_workspace):
    try:
        initialise_base_dirs(webapp_config=webapp_config)
        yield
    finally:
        _cleanup_dirs(webapp_config)
