from functools import cache

import httpx

from config.news_scheduler_settings import get_setting


@cache
def http_client() -> httpx.Client:
    """Shared HTTP client, created lazily on first use (after settings are loaded)."""
    return httpx.Client(
        timeout=get_setting("HTTP_TIMEOUT_SECONDS"), follow_redirects=True
    )
