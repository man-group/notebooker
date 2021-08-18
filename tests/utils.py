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


def _all_templates():
    web_config = WebappConfig(
        PY_TEMPLATE_BASE_DIR="",
        SERIALIZER_CLS=DEFAULT_SERIALIZER,
        SERIALIZER_CONFIG={},
        SCHEDULER_MONGO_COLLECTION="jobs",
        SCHEDULER_MONGO_DATABASE="apscheduler",
    )
    flask_app = create_app()
    flask_app = setup_app(flask_app, web_config)
    with flask_app.app_context():
        templates = list(_gen_all_templates(get_all_possible_templates(warn_on_local=False)))
        return templates
