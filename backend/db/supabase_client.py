# SPDX-License-Identifier: AGPL-3.0-only
"""
Supabase client — resilient singleton for the entire backend.

Returns None if credentials are not configured, allowing the app
to run in demo mode without crashing.
"""

from __future__ import annotations

from typing import Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("crimescope.db")

_client = None
_initialised = False


def get_supabase():
    """
    Get the Supabase client, or None if unavailable.

    Usage:
        from backend.db.supabase_client import get_supabase
        client = get_supabase()
        if client:
            client.table("cases").select("*").execute()
    """
    global _client, _initialised
    if _initialised:
        return _client

    _initialised = True

    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.warning("Supabase not configured — database unavailable")
        return None

    try:
        from supabase import create_client
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("Supabase client initialised")
        return _client
    except Exception as e:
        logger.error(f"Supabase initialisation failed: {e}")
        return None


# Backward-compatible alias — returns client or None
supabase = get_supabase()
