import errno
import os
from logging import getLogger

from notebooker.serialization.serialization import get_serializer_from_cls
from notebooker.utils.results import get_latest_successful_job_results_all_params

logger = getLogger(__name__)


def snap_latest_successful_notebooks(config, report_name):
    result_serializer = get_serializer_from_cls(config.SERIALIZER_CLS, **config.SERIALIZER_CONFIG)
    report_suffix = report_name.split("/")[-1]
    report_directory = os.path.join(config.OUTPUT_DIR, report_suffix)
    results = get_latest_successful_job_results_all_params(report_name, result_serializer)
    _write_results(results, report_directory)


def _write_results(results, directory):
    for result in results:
        _write_notebook_html(result, directory)
        _write_notebook_outputs(result, directory)


def _write_notebook_outputs(result, directory):
    for path, output in result.raw_html_resources["outputs"].items():
        output_path = os.path.join(directory, path)
        _create_dirs_if_not_present(output_path)
        logger.info("Writing resources to {}".format(output_path))
        with open(output_path, "wb") as output_file:
            output_file.write(output)


def _write_notebook_html(result, directory):
    override_str = "".join(["{}_{}".format(x, y) for x, y in result.overrides.items()])
    save_file_name = "{}.html".format(override_str)
    save_file_path = os.path.join(directory, save_file_name)
    logger.info("Writing notebook result to {}".format(save_file_path))
    _create_dirs_if_not_present(save_file_path)
    with open(save_file_path, "w") as save_file:
        save_file.write(result.raw_html)


def _create_dirs_if_not_present(filename):
    try:
        os.makedirs(os.path.dirname(filename))
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
