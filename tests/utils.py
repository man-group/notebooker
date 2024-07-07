from flask import Flask

from notebooker.constants import DEFAULT_SERIALIZER
from notebooker.settings import WebappConfig
from notebooker.web.app import create_app, setup_app
from notebooker.web.utils import get_all_possible_templates


def _gen_all_templates(template_dict):
    for template_name, children in template_dict.items():
        if children:
            yield from _gen_all_templates(children)
        else:
            yield template_name


def all_templates():
    web_config = WebappConfig(
        PY_TEMPLATE_BASE_DIR="",
        SERIALIZER_CLS=DEFAULT_SERIALIZER,
        SERIALIZER_CONFIG={},
        SCHEDULER_MONGO_COLLECTION="jobs",
        SCHEDULER_MONGO_DATABASE="apscheduler",
    )
    flask_app = Flask("test")
    flask_app.config.from_object(web_config)
    with flask_app.app_context():
        templates = list(_gen_all_templates(get_all_possible_templates(warn_on_local=False)))
        return templates


def templates_with_local_context():
    templates = all_templates()
    return list(filter(lambda x: x.startswith("local_context"), templates))


def templates_without_local_context():
    templates = all_templates()
    return list(filter(lambda x: not x.startswith("local_context"), templates))
