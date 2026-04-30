"""
Module-level state for the active notebooker config.

This is read by code that runs in scheduler-triggered jobs (e.g.
``notebooker.web.scheduler.run_report``) and by webapp shutdown handlers.
It lives here, not on ``notebooker.web.app``, so the standalone scheduler
can populate it without importing the Flask/gevent stack.
"""
from typing import Optional

from notebooker.settings import BaseConfig

GLOBAL_CONFIG: Optional[BaseConfig] = None
