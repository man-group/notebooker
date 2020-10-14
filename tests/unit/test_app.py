import os
import pytest

from notebooker.web.config import settings


@pytest.fixture
def dev_config():
    return settings.DevConfig


@pytest.fixture
def prod_config():
    return settings.ProdConfig


def safe_setup_env_vars():
    """Return a copy of the environment after running setup_env_vars."""
    original_env = os.environ.copy()

    try:
        setup_env_vars()
        return os.environ.copy()
    finally:
        os.environ.clear()
        os.environ.update(original_env)


def test_setup_env_vars(dev_config):
    env = safe_setup_env_vars()
    assert env["PORT"] == str(dev_config.PORT)
    assert env["MONGO_HOST"] == str(dev_config.MONGO_HOST)


def test_setup_env_vars_override_default(monkeypatch, dev_config):
    monkeypatch.setenv("MONGO_HOST", "override")
    env = safe_setup_env_vars()
    assert env["PORT"] == str(dev_config.PORT)
    assert env["MONGO_HOST"] == "override"


def test_setup_env_vars_prod(monkeypatch, prod_config):
    monkeypatch.setenv("NOTEBOOKER_ENVIRONMENT", "Prod")
    env = safe_setup_env_vars()
    assert env["PORT"] == str(prod_config.PORT)
    assert env["MONGO_HOST"] == str(prod_config.MONGO_HOST)
