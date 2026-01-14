import mock
import signal

from notebooker.standalone_scheduler import run_standalone_scheduler, _shutdown_handler


class TestStandaloneScheduler:
    def test_sets_global_config(self, webapp_config):
        """Test that run_standalone_scheduler sets GLOBAL_CONFIG."""
        with mock.patch("notebooker.standalone_scheduler.get_jobstore_config") as mock_get_config:
            with mock.patch("notebooker.standalone_scheduler.create_scheduler") as mock_create:
                with mock.patch("notebooker.standalone_scheduler.signal.signal"):
                    with mock.patch("notebooker.standalone_scheduler.time.sleep", side_effect=KeyboardInterrupt):
                        with mock.patch("notebooker.standalone_scheduler._shutdown_handler"):
                            mock_get_config.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
                            mock_scheduler = mock.MagicMock()
                            mock_create.return_value = mock_scheduler

                            # Import the app module to check GLOBAL_CONFIG
                            from notebooker.web import app as app_module
                            original_config = app_module.GLOBAL_CONFIG

                            try:
                                run_standalone_scheduler(webapp_config)
                            except (KeyboardInterrupt, SystemExit):
                                pass

                            # Verify GLOBAL_CONFIG was set
                            assert app_module.GLOBAL_CONFIG is webapp_config

                            # Restore original
                            app_module.GLOBAL_CONFIG = original_config

    def test_creates_scheduler_not_paused(self, webapp_config):
        """Test that standalone scheduler is created without pausing."""
        with mock.patch("notebooker.standalone_scheduler.get_jobstore_config") as mock_get_config:
            with mock.patch("notebooker.standalone_scheduler.create_scheduler") as mock_create:
                with mock.patch("notebooker.standalone_scheduler.signal.signal"):
                    with mock.patch("notebooker.standalone_scheduler.time.sleep", side_effect=KeyboardInterrupt):
                        with mock.patch("notebooker.standalone_scheduler._shutdown_handler"):
                            mock_get_config.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
                            mock_scheduler = mock.MagicMock()
                            mock_create.return_value = mock_scheduler

                            try:
                                run_standalone_scheduler(webapp_config)
                            except (KeyboardInterrupt, SystemExit):
                                pass

                            # Verify scheduler was created with paused=False
                            mock_create.assert_called_once()
                            call_args = mock_create.call_args
                            assert call_args[1].get("paused", False) is False

    def test_registers_signal_handlers(self, webapp_config):
        """Test that SIGTERM and SIGINT handlers are registered."""
        with mock.patch("notebooker.standalone_scheduler.get_jobstore_config") as mock_get_config:
            with mock.patch("notebooker.standalone_scheduler.create_scheduler") as mock_create:
                with mock.patch("notebooker.standalone_scheduler.signal.signal") as mock_signal:
                    with mock.patch("notebooker.standalone_scheduler.time.sleep", side_effect=KeyboardInterrupt):
                        with mock.patch("notebooker.standalone_scheduler._shutdown_handler"):
                            mock_get_config.return_value = {"client": mock.MagicMock(), "database": "db", "collection": "coll"}
                            mock_scheduler = mock.MagicMock()
                            mock_create.return_value = mock_scheduler

                            try:
                                run_standalone_scheduler(webapp_config)
                            except (KeyboardInterrupt, SystemExit):
                                pass

                            # Verify signal handlers were registered
                            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
                            assert signal.SIGTERM in signal_calls
                            assert signal.SIGINT in signal_calls


class TestShutdownHandler:
    def test_shutdown_handler_shuts_down_scheduler(self):
        """Test that _shutdown_handler properly shuts down the scheduler."""
        import notebooker.standalone_scheduler as scheduler_module

        mock_scheduler = mock.MagicMock()
        scheduler_module._scheduler = mock_scheduler

        with mock.patch("notebooker.standalone_scheduler.sys.exit") as mock_exit:
            _shutdown_handler(signal.SIGTERM, None)

            mock_scheduler.shutdown.assert_called_once_with(wait=True)
            mock_exit.assert_called_once_with(0)

        # Clean up
        scheduler_module._scheduler = None

    def test_shutdown_handler_handles_no_scheduler(self):
        """Test that _shutdown_handler handles case when scheduler is None."""
        import notebooker.standalone_scheduler as scheduler_module

        scheduler_module._scheduler = None

        with mock.patch("notebooker.standalone_scheduler.sys.exit") as mock_exit:
            _shutdown_handler(signal.SIGTERM, None)

            mock_exit.assert_called_once_with(0)
