from mock import MagicMock, patch, sentinel

import notebooker.utils.results as results
from notebooker import constants


def test_get_latest_job_results():
    serializer = MagicMock()
    serializer.get_latest_job_id_for_name_and_params.return_value = sentinel.latest_job_id
    with patch("notebooker.utils.results._get_job_results", return_value=sentinel.result) as get_results:
        result = results.get_latest_job_results(
            sentinel.report_name, sentinel.report_params, serializer, sentinel.retrying, sentinel.ignore_cache
        )
    assert result == sentinel.result
    get_results.assert_called_once_with(
        sentinel.latest_job_id, sentinel.report_name, serializer, sentinel.retrying, sentinel.ignore_cache
    )
    serializer.get_latest_job_id_for_name_and_params.assert_called_once_with(
        sentinel.report_name, sentinel.report_params, None
    )


def test_missing_latest_job_results():
    serializer = MagicMock()
    serializer.get_latest_job_id_for_name_and_params.return_value = None
    with patch("notebooker.utils.results._get_job_results") as get_results:
        result = results.get_latest_job_results(
            sentinel.report_name, sentinel.report_params, serializer, sentinel.retrying, sentinel.ignore_cache
        )
    get_results.assert_not_called()
    assert isinstance(result, constants.NotebookResultError)
    assert result.report_name == sentinel.report_name
    assert result.job_id is None
    assert result.overrides == sentinel.report_params


def test_get_results_from_name_and_params():
    job_id_func = MagicMock()
    job_id_func.return_value = sentinel.latest_job_id
    with patch("notebooker.utils.results._get_job_results", return_value=sentinel.result) as get_results:
        result = results._get_results_from_name_and_params(
            job_id_func,
            sentinel.report_name,
            sentinel.report_params,
            sentinel.serializer,
            sentinel.retrying,
            sentinel.ignore_cache,
        )
    assert result == sentinel.result
    get_results.assert_called_once_with(
        sentinel.latest_job_id, sentinel.report_name, sentinel.serializer, sentinel.retrying, sentinel.ignore_cache
    )
    job_id_func.assert_called_once_with(sentinel.report_name, sentinel.report_params, None)


def test_get_results_from_name_and_params_as_of():
    job_id_func = MagicMock()
    job_id_func.return_value = sentinel.latest_job_id
    with patch("notebooker.utils.results._get_job_results", return_value=sentinel.result) as get_results:
        result = results._get_results_from_name_and_params(
            job_id_func,
            sentinel.report_name,
            sentinel.report_params,
            sentinel.serializer,
            sentinel.retrying,
            sentinel.ignore_cache,
            sentinel.as_of,
        )
    assert result == sentinel.result
    get_results.assert_called_once_with(
        sentinel.latest_job_id, sentinel.report_name, sentinel.serializer, sentinel.retrying, sentinel.ignore_cache
    )
    job_id_func.assert_called_once_with(sentinel.report_name, sentinel.report_params, sentinel.as_of)


@patch("notebooker.utils.results._get_results_from_name_and_params")
def test_get_latest_successful_job_results(_get_results_from_name_and_params):
    serializer = MagicMock()
    results.get_latest_successful_job_results(
        sentinel.report_name, sentinel.report_params, serializer, sentinel.retrying, sentinel.ignore_cache
    )

    _get_results_from_name_and_params.assert_called_once_with(
        serializer.get_latest_successful_job_id_for_name_and_params,
        sentinel.report_name,
        sentinel.report_params,
        serializer,
        sentinel.retrying,
        sentinel.ignore_cache,
        None,
    )


@patch("notebooker.utils.results._get_results_from_name_and_params")
def test_get_latest_successful_job_results_as_of(_get_results_from_name_and_params):
    serializer = MagicMock()
    results.get_latest_successful_job_results(
        sentinel.report_name,
        sentinel.report_params,
        serializer,
        sentinel.retrying,
        sentinel.ignore_cache,
        sentinel.as_of,
    )

    _get_results_from_name_and_params.assert_called_once_with(
        serializer.get_latest_successful_job_id_for_name_and_params,
        sentinel.report_name,
        sentinel.report_params,
        serializer,
        sentinel.retrying,
        sentinel.ignore_cache,
        sentinel.as_of,
    )


@patch("notebooker.utils.results._get_job_results")
def test_get_latest_successful_job_results_all_params(_get_job_results):
    serializer = MagicMock()
    serializer.get_latest_successful_job_ids_for_name_all_params.return_value = [sentinel.job_id]
    _get_job_results.return_value = sentinel.results
    res = results.get_latest_successful_job_results_all_params(
        sentinel.report_name, serializer, sentinel.retrying, sentinel.ignore_cache
    )
    all_results = [r for r in res]
    serializer.get_latest_successful_job_ids_for_name_all_params.assert_called_once_with(sentinel.report_name)
    _get_job_results.assert_called_once_with(
        sentinel.job_id, sentinel.report_name, serializer, sentinel.retrying, sentinel.ignore_cache
    )
    assert len(all_results) == 1
    assert all_results[0] == sentinel.results
