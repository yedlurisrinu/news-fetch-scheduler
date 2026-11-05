"""
### Unit tests for src/newsfeed/fetch_all_articles.py
Tests orchestration: RSS + API combination, Kafka publish trigger, and empty-list guard.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from newsfeed.fetch_all_articles import fetch_all_articles

_RSS_ARTICLE = {
    "source": "BBC", "title": "RSS Story", "summary": "Summary",
    "link": "http://bbc.com/1", "published_at": "2026-03-28T10:00:00+00:00",
    "fetched_at": "2026-03-28T10:01:00+00:00",
}
_API_ARTICLE = {
    "source": "NewsAPI", "title": "API Story", "summary": "Summary",
    "link": "http://newsapi.com/1", "published_at": "2026-03-28T09:00:00Z",
    "fetched_at": "2026-03-28T10:01:00+00:00",
}


class TestFetchAllArticles:

    ### Combination and return value

    def test_combines_rss_and_api_articles(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[_API_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka"):
            result = fetch_all_articles()

        assert len(result) == 2
        assert _RSS_ARTICLE in result
        assert _API_ARTICLE in result

    def test_returns_list(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka"):
            result = fetch_all_articles()

        assert isinstance(result, list)

    def test_rss_articles_come_before_api_articles(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[_API_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka"):
            result = fetch_all_articles()

        assert result[0] == _RSS_ARTICLE
        assert result[1] == _API_ARTICLE

    ### Kafka publishing trigger

    def test_calls_publish_when_articles_exist(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[_API_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka") as mock_publish:
            fetch_all_articles()

        mock_publish.assert_called_once_with([_RSS_ARTICLE, _API_ARTICLE])

    def test_does_not_call_publish_when_no_articles(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka") as mock_publish:
            fetch_all_articles()

        mock_publish.assert_not_called()

    def test_calls_publish_with_only_rss_when_api_empty(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka") as mock_publish:
            fetch_all_articles()

        mock_publish.assert_called_once_with([_RSS_ARTICLE])

    def test_calls_publish_with_only_api_when_rss_empty(self):
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[_API_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka") as mock_publish:
            fetch_all_articles()

        mock_publish.assert_called_once_with([_API_ARTICLE])

    ### Debug logging branch (lines 28-32)

    def test_debug_logs_rss_and_api_articles_when_level_is_debug(self):
        import logging
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[_API_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka"), \
             patch("newsfeed.fetch_all_articles.logger") as mock_logger:
            mock_logger.isEnabledFor.return_value = True
            fetch_all_articles()

        debug_calls = [str(c) for c in mock_logger.debug.call_args_list]
        assert any("RSS" in c for c in debug_calls)
        assert any("API" in c for c in debug_calls)

    def test_debug_block_not_entered_when_level_is_info(self):
        import logging
        with patch("newsfeed.fetch_all_articles.fetch_rss_articles", return_value=[_RSS_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.fetch_api_articles", return_value=[_API_ARTICLE]), \
             patch("newsfeed.fetch_all_articles.publisher.publish_to_kafka"), \
             patch("newsfeed.fetch_all_articles.logger") as mock_logger:
            mock_logger.isEnabledFor.return_value = False
            fetch_all_articles()

        mock_logger.debug.assert_not_called()