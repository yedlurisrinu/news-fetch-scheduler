"""
### Unit tests for src/newsfeed/api_feed.py
Tests NewsAPI HTTP fetching, article mapping, error handling, and API key injection.
"""
import pytest
from unittest.mock import MagicMock, patch

from newsfeed.api_feed import fetch_api_articles


def _mock_response(articles: list, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"articles": articles}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


def _patch_get(**kwargs):
    """Patch the shared HTTP client used by api_feed; kwargs configure client.get."""
    client = MagicMock()
    client.get = MagicMock(**kwargs)
    return patch("newsfeed.api_feed.http_client", return_value=client)


_SAMPLE_ITEM = {
    "title": "AI Breakthrough",
    "description": "Researchers discover new model.",
    "url": "https://newsapi.org/article/1",
    "publishedAt": "2026-03-28T10:00:00Z",
    "source": {"name": "TechCrunch"},
}


class TestFetchApiArticles:

    ### Successful fetch

    def test_returns_list_of_dicts(self):
        with _patch_get(return_value=_mock_response([_SAMPLE_ITEM])):
            result = fetch_api_articles()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_maps_fields_correctly(self):
        with _patch_get(return_value=_mock_response([_SAMPLE_ITEM])):
            result = fetch_api_articles()

        article = result[0]
        assert article["title"] == "AI Breakthrough"
        assert article["summary"] == "Researchers discover new model."
        assert article["link"] == "https://newsapi.org/article/1"
        assert article["published_at"] == "2026-03-28T10:00:00Z"
        assert article["source"] == "TechCrunch"
        assert "fetched_at" in article

    def test_returns_empty_list_when_no_articles_key(self):
        response = MagicMock()
        response.json.return_value = {}
        response.raise_for_status = MagicMock()
        with _patch_get(return_value=response):
            result = fetch_api_articles()
        assert result == []

    def test_multiple_articles_all_mapped(self):
        items = [_SAMPLE_ITEM, {**_SAMPLE_ITEM, "title": "Second Story", "url": "https://newsapi.org/2"}]
        with _patch_get(return_value=_mock_response(items)):
            result = fetch_api_articles()
        assert len(result) == 2

    ### API key injection

    def test_api_key_sent_as_header_not_query_param(self):
        with _patch_get(return_value=_mock_response([])) as mock_factory, \
             patch("newsfeed.api_feed.os.getenv", return_value="test-api-key"):
            fetch_api_articles()

        call_kwargs = mock_factory.return_value.get.call_args[1]
        assert call_kwargs["headers"]["X-Api-Key"] == "test-api-key"
        assert "apiKey" not in call_kwargs["params"]

    def test_http_client_timeout_from_settings(self):
        import httpx
        from common.http_client import http_client
        from config.news_scheduler_settings import get_setting
        http_client.cache_clear()
        try:
            with patch("common.http_client.httpx.Client") as mock_client:
                http_client()
            mock_client.assert_called_once_with(timeout=get_setting('HTTP_TIMEOUT_SECONDS'),
                                                follow_redirects=True)
            assert get_setting('HTTP_TIMEOUT_SECONDS') == 10
        finally:
            http_client.cache_clear()

    ### Missing source name

    def test_falls_back_to_newsapi_when_source_missing(self):
        item = {**_SAMPLE_ITEM, "source": {}}
        with _patch_get(return_value=_mock_response([item])):
            result = fetch_api_articles()
        assert result[0]["source"] == "NewsAPI"

    ### Error handling

    def test_returns_empty_list_on_http_error(self):
        with _patch_get(return_value=_mock_response([], status_code=401)):
            result = fetch_api_articles()
        assert result == []

    def test_returns_empty_list_on_connection_error(self):
        with _patch_get(side_effect=Exception("connection refused")):
            result = fetch_api_articles()
        assert result == []

    def test_http_error_log_omits_exception_text(self, caplog):
        import httpx
        import logging
        with _patch_get(side_effect=httpx.ConnectError("https://x?apiKey=SECRET")), \
             caplog.at_level(logging.WARNING):
            fetch_api_articles()
        assert "ConnectError" in caplog.text
        assert "SECRET" not in caplog.text

    def test_status_error_logs_status_code_only(self, caplog):
        import logging
        with _patch_get(return_value=_mock_response([], status_code=401)), \
             caplog.at_level(logging.WARNING):
            fetch_api_articles()
        assert "401" in caplog.text

    def test_does_not_raise_on_any_exception(self):
        with _patch_get(side_effect=RuntimeError("boom")):
            result = fetch_api_articles()  # must not raise
        assert isinstance(result, list)