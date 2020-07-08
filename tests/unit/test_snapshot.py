from __future__ import unicode_literals

import mock
from click.testing import CliRunner
from six import PY3

from notebooker import constants, snapshot


def test_snapshot_latest_successful_notebooks():
    compat_builtin = "builtins.open" if PY3 else "__builtin__.open"
    with mock.patch(compat_builtin) as fopen:
        with mock.patch("notebooker.snapshot.get_latest_successful_job_results_all_params") as get_results:
            with mock.patch("notebooker.snapshot.get_serializer_from_cls") as nbs:
                result = mock.Mock(spec=constants.NotebookResultComplete)
                result.overrides = {"over": "ride"}
                result.raw_html = "some html"
                result.raw_html_resources = {"outputs": {"out/put/img.png": "blah"}}
                get_results.return_value = [result]
                output_dir = "html_output_dir"
                report_name = "my/test_report"
                runner = CliRunner()

                cli_result = runner.invoke(
                    snapshot.snapshot_latest_successful_notebooks,
                    ["--report-name", report_name, "--output-directory", output_dir],
                )

                assert cli_result.exit_code == 0
                fopen.assert_any_call("html_output_dir/test_report/over_ride.html", "w")
                fopen().__enter__().write.assert_any_call("some html")
                fopen.assert_any_call("html_output_dir/test_report/out/put/img.png", "wb")
                fopen().__enter__().write.assert_any_call("blah")


@mock.patch("notebooker.snapshot._write_notebook_html")
@mock.patch("notebooker.snapshot._write_notebook_outputs")
def test_write_results(_write_notebook_outputs, _write_notebook_html):
    results = [mock.sentinel.result1, mock.sentinel.result2]
    snapshot._write_results(results, mock.sentinel.directory)
    _write_notebook_html.assert_has_calls(
        [
            mock.call(mock.sentinel.result1, mock.sentinel.directory),
            mock.call(mock.sentinel.result2, mock.sentinel.directory),
        ]
    )
    _write_notebook_outputs.assert_has_calls(
        [
            mock.call(mock.sentinel.result1, mock.sentinel.directory),
            mock.call(mock.sentinel.result2, mock.sentinel.directory),
        ]
    )


def test_write_notebook_html():
    compat_builtin = "builtins.open" if PY3 else "__builtin__.open"
    output_dir = "output_dir"
    result = mock.Mock(spec=constants.NotebookResultComplete)
    result.overrides = {"over": "ride"}
    result.raw_html = "some html"
    with mock.patch(compat_builtin) as fopen:
        snapshot._write_notebook_html(result, output_dir)
        fopen.assert_any_call("output_dir/over_ride.html", "w")
        fopen().__enter__().write.assert_any_call("some html")


def test_write_notebook_outputs():
    compat_builtin = "builtins.open" if PY3 else "__builtin__.open"
    output_dir = "output_dir"
    result = mock.Mock(spec=constants.NotebookResultComplete)
    result.raw_html_resources = {"outputs": {"out/put/img.png": "blah"}}
    with mock.patch(compat_builtin) as fopen:
        snapshot._write_notebook_outputs(result, output_dir)
        fopen.assert_any_call("output_dir/out/put/img.png", "wb")
        fopen().__enter__().write.assert_any_call("blah")
