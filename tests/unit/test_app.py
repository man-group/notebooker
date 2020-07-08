import os

from notebooker.web.app import setup_env_vars


def test_setup_env_vars():
    set_vars = setup_env_vars()
    try:
        assert os.getenv("PORT") == "11828"
        assert os.getenv("MONGO_HOST") == "localhost"
    finally:
        for var in set_vars:
            del os.environ[var]


def test_setup_env_vars_override_default():
    os.environ["MONGO_HOST"] = "override"
    set_vars = setup_env_vars()
    try:
        assert os.getenv("PORT") == "11828"
        assert os.getenv("MONGO_HOST") == "override"
    finally:
        for var in set_vars:
            del os.environ[var]
        del os.environ["MONGO_HOST"]


def test_setup_env_vars_prod():
    os.environ["NOTEBOOKER_ENVIRONMENT"] = "Prod"
    set_vars = setup_env_vars()
    try:
        assert os.getenv("PORT") == "11828"
        assert os.getenv("MONGO_HOST") == "a-production-mongo-cluster"
    finally:
        for var in set_vars:
            del os.environ[var]
        del os.environ["NOTEBOOKER_ENVIRONMENT"]
