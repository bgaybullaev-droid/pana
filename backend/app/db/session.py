"""Backward-compat re-export: async_session_factory → async_session_maker.

Several worker tasks import ``async_session_factory`` from this module.
The canonical name is ``async_session_maker`` in ``app.db.database``;
this shim keeps those callers working without touching every file.
"""

from app.db.database import async_session_maker as async_session_factory

__all__ = ["async_session_factory"]
