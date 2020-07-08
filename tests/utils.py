import decorator

from notebooker.utils.filesystem import initialise_base_dirs, _cleanup_dirs
from notebooker.utils.templates import get_all_possible_templates


def setup_and_cleanup_notebooker_filesystem(f):
    def blast_it(func, *args, **kwargs):
        try:
            initialise_base_dirs()
            result = func(*args, **kwargs)
            return result
        finally:
            _cleanup_dirs()

    return decorator.decorator(blast_it, f)


def _gen_all_templates(template_dict):
    for template_name, children in template_dict.items():
        if children:
            yield from _gen_all_templates(children)
        else:
            yield template_name


def _all_templates():
    templates = list(_gen_all_templates(get_all_possible_templates(warn_on_local=False)))
    return templates
