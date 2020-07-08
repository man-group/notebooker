import pytest

TEST_DB_NAME = "notebookertest"
TEST_LIB = "NB_OUTPUT"


@pytest.fixture
def bson_library(mongo_server):
    return mongo_server.api[TEST_DB_NAME][TEST_LIB]


@pytest.fixture
def mongo_host(mongo_server):
    return f"{mongo_server.hostname}:{mongo_server.port}"


@pytest.fixture
def test_db_name():
    return TEST_DB_NAME


@pytest.fixture
def test_lib_name():
    return TEST_LIB
