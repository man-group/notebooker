import mock
import signal

from notebooker.standalone_scheduler import run_standalone_scheduler, _shutdown_handler


def _patches():
    """Common patches for run_standalone_scheduler tests."""
    return (
        mock.patch("notebooker.standalone_scheduler.get_jobstore_config"),
        mock.patch("notebooker.standalone_scheduler.create_blocking_scheduler"),
        mock.patch("notebooker.standalone_scheduler.signal.signal"),
        mock.patch("notebooker.standalone_scheduler._start_liveness_probe"),
    )


class TestStandaloneScheduler:
    def test_sets_global_config(self, webapp_config):
        """Test that run_standalone_scheduler sets GLOBAL_CONFIG on notebooker.global_config."""
        mock_get_config, mock_create, mock_signal, mock_liveness = _patches()
        with mock_get_config as mgc, mock_create as mc, mock_signal, mock_liveness:
            mgc.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
            mock_scheduler = mock.MagicMock()
            mc.return_value = mock_scheduler

            from notebooker import global_config

            original_config = global_config.GLOBAL_CONFIG
            try:
                run_standalone_scheduler(webapp_config)
                assert global_config.GLOBAL_CONFIG is webapp_config
            finally:
                global_config.GLOBAL_CONFIG = original_config

    def test_creates_blocking_scheduler(self, webapp_config):
        """Test that the standalone scheduler uses create_blocking_scheduler with the jobstore config."""
        mock_get_config, mock_create, mock_signal, mock_liveness = _patches()
        with mock_get_config as mgc, mock_create as mc, mock_signal, mock_liveness:
            jobstore = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
            mgc.return_value = jobstore
            mock_scheduler = mock.MagicMock()
            mc.return_value = mock_scheduler

            run_standalone_scheduler(webapp_config)

            mc.assert_called_once_with(jobstore)
            mock_scheduler.start.assert_called_once_with()

    def test_registers_signal_handlers(self, webapp_config):
        """Test that SIGTERM and SIGINT handlers are registered."""
        mock_get_config, mock_create, mock_signal_p, mock_liveness = _patches()
        with mock_get_config as mgc, mock_create as mc, mock_signal_p as ms, mock_liveness:
            mgc.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
            mc.return_value = mock.MagicMock()

            run_standalone_scheduler(webapp_config)

            signal_calls = [call[0][0] for call in ms.call_args_list]
            assert signal.SIGTERM in signal_calls
            assert signal.SIGINT in signal_calls

    def test_starts_liveness_probe_when_port_set(self, webapp_config):
        """Liveness probe is started when LIVENESS_PORT is non-zero."""
        mock_get_config, mock_create, mock_signal, mock_liveness = _patches()
        with mock_get_config as mgc, mock_create as mc, mock_signal, mock_liveness as ml:
            mgc.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
            mc.return_value = mock.MagicMock()
            webapp_config.LIVENESS_PORT = 12345

            run_standalone_scheduler(webapp_config)

            ml.assert_called_once_with(12345)

    def test_skips_liveness_probe_when_port_zero(self, webapp_config):
        """Liveness probe is skipped when LIVENESS_PORT is 0."""
        mock_get_config, mock_create, mock_signal, mock_liveness = _patches()
        with mock_get_config as mgc, mock_create as mc, mock_signal, mock_liveness as ml:
            mgc.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
            mc.return_value = mock.MagicMock()
            webapp_config.LIVENESS_PORT = 0

            run_standalone_scheduler(webapp_config)

            ml.assert_not_called()


class TestShutdownHandler:
    def test_shutdown_handler_shuts_down_scheduler(self):
        """Test that _shutdown_handler properly shuts down the scheduler."""
        import notebooker.standalone_scheduler as scheduler_module

        mock_scheduler = mock.MagicMock()
        scheduler_module._scheduler = mock_scheduler
        try:
            _shutdown_handler(signal.SIGTERM, None)
            mock_scheduler.shutdown.assert_called_once_with(wait=True)
        finally:
            scheduler_module._scheduler = None

    def test_shutdown_handler_handles_no_scheduler(self):
        """Test that _shutdown_handler handles case when scheduler is None."""
        import notebooker.standalone_scheduler as scheduler_module

        scheduler_module._scheduler = None
        # Should not raise.
        _shutdown_handler(signal.SIGTERM, None)
