import errno
import logging
import os
import shutil
import uuid

logger = logging.getLogger(__name__)


def initialise_base_dirs(output_dir=None, template_dir=None, cache_dir=None):
    output_dir = (
        output_dir
        or os.getenv("OUTPUT_DIR")
        or os.path.join(os.path.expanduser("~"), ".notebooker", "output", str(uuid.uuid4()))
    )
    logger.info("Creating output base dir: %s", output_dir)
    mkdir_p(output_dir)
    os.environ["OUTPUT_DIR"] = output_dir

    template_dir = (
        template_dir
        or os.getenv("TEMPLATE_DIR")
        or os.path.join(os.path.expanduser("~"), ".notebooker", "templates", str(uuid.uuid4()))
    )
    logger.info("Creating templates base dir: %s", template_dir)
    mkdir_p(template_dir)
    os.environ["TEMPLATE_DIR"] = template_dir

    cache_dir = (
        cache_dir
        or os.getenv("CACHE_DIR")
        or os.path.join(os.path.expanduser("~"), ".notebooker", "webcache", str(uuid.uuid4()))
    )
    logger.info("Creating webcache dir: %s", cache_dir)
    mkdir_p(cache_dir)
    os.environ["CACHE_DIR"] = cache_dir
    return output_dir, template_dir, cache_dir


def get_output_dir():
    return os.getenv("OUTPUT_DIR")


def get_template_dir():
    return os.getenv("TEMPLATE_DIR")


def get_cache_dir():
    return os.getenv("CACHE_DIR")


def mkdir_p(path):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def _cleanup_dirs():
    for d in (get_output_dir(), get_template_dir(), get_cache_dir()):
        if d and os.path.exists(d):
            logger.info("Cleaning up %s", d)
            shutil.rmtree(d)
