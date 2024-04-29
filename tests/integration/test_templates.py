from notebooker.web.utils import get_all_possible_templates


def test_get_all_possible_templates(flask_app):
    flask_app.config["PY_TEMPLATE_BASE_DIR"] = None
    with flask_app.app_context():
        assert get_all_possible_templates() == {
            "sample": {
                "sample/plot_random": None,
                "sample/test_plotly": None,
                "sample/plot_random_raw": None,
                "sample/slideshow_test": None,
            },
            "other_folder": {
                "other_folder/other_slideshow_test": None,
                "this one has spaces": {
                    "other_folder/this one has spaces/plot_random2": None,
                },
            },
        }
