from dataclasses import asdict

from notebooker.settings import WebappConfig


def test_config_reversible(flask_app, webapp_config):
    flask_app.config["DEBUG"] = True
    webapp_config.DEBUG = True  # We don't care about deserialising DEBUG from the flask config (famous last words)
    assert asdict(WebappConfig.from_superset_kwargs(flask_app.config)) == asdict(webapp_config)
