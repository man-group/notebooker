# FIXME move to notebooker/web
import errno
import logging
import os
import shutil
import uuid

from flask import current_app

from notebooker.settings import WebappConfig

logger = logging.getLogger(__name__)


def initialise_base_dirs(webapp_config: WebappConfig = None, output_dir=None, template_dir=None, cache_dir=None):
    output_dir = output_dir or (webapp_config.OUTPUT_DIR if webapp_config else None)
    if output_dir:
        logger.info("Creating output base dir: %s", output_dir)
        mkdir_p(output_dir)

    template_dir = template_dir or (webapp_config.TEMPLATE_DIR if webapp_config else None)
    if template_dir:
        logger.info("Creating templates base dir: %s", template_dir)
        mkdir_p(template_dir)

    cache_dir = cache_dir or (webapp_config.CACHE_DIR if webapp_config else None)
    if cache_dir:
        logger.info("Creating webcache dir: %s", cache_dir)
        mkdir_p(cache_dir)
    return output_dir, template_dir, cache_dir


def mkdir_p(path):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def get_cache_dir():
    return current_app.config["CACHE_DIR"]


def get_output_dir():
    return current_app.config["OUTPUT_DIR"]


def get_template_dir():
    return current_app.config["TEMPLATE_DIR"]


def _cleanup_dirs(webapp_config):
    for d in (webapp_config.OUTPUT_DIR, webapp_config.TEMPLATE_DIR, webapp_config.CACHE_DIR):
        if d and os.path.exists(d):
            logger.info("Cleaning up %s", d)
            shutil.rmtree(d)
