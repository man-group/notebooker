import retrying
from cachelib.file import FileSystemCache

from notebooker.utils.filesystem import get_cache_dir

cache = None


def _cache_key(report_name, job_id):
    return "report_name={}&job_id={}".format(report_name, job_id)


@retrying.retry(stop_max_attempt_number=3)
def get_cache(key, cache_dir=None):
    global cache
    if cache is None:
        cache = FileSystemCache(cache_dir or get_cache_dir())
    return cache.get(str(key))


def get_report_cache(report_name, job_id, cache_dir=None):
    return get_cache(_cache_key(report_name, job_id), cache_dir=cache_dir)


@retrying.retry(stop_max_attempt_number=3)
def set_cache(key, value, timeout=15, cache_dir=None):
    global cache
    if cache is None:
        cache = FileSystemCache(cache_dir or get_cache_dir())
    cache.set(str(key), value, timeout=timeout)


def set_report_cache(report_name, job_id, value, timeout=15, cache_dir=None):
    if value:
        set_cache(_cache_key(report_name, job_id), value, timeout=timeout, cache_dir=cache_dir)
