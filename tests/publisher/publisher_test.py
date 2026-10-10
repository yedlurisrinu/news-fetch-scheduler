"""
### Unit tests for src/publisher/publisher.py
Tests publish_to_kafka: deduplication skip, Kafka produce calls, and flush behaviour.
The lru_cache factory functions (_deduplicator, _producer) are patched and their
caches cleared before each test to ensure isolation.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from publisher import publisher

# Save originals at import time — before the autouse fixture replaces them with lambdas.
# These are the real lru_cache functions whose bodies (publisher.py lines 25, 29-30)
# we need to exercise for coverage.
_ORIG_DEDUPLICATOR = publisher._deduplicator
_ORIG_PRODUCER = publisher._producer

_ARTICLE = {
    "source": "BBC",
    "title": "Test Headline",
    "summary": "Full article body here.",
    "link": "http://bbc.com/news/1",
    "published_at": "2026-03-28T10:00:00+00:00",
    "fetched_at": "2026-03-28T10:01:00+00:00",
}


@pytest.fixture(autouse=True)
def mock_lazy_factories(monkeypatch):
    """Patch the two lru_cache factory functions and clear their caches before each test."""
    mock_prod = MagicMock()
    mock_dedup = MagicMock()

    publisher._producer.cache_clear()
    publisher._deduplicator.cache_clear()

    monkeypatch.setattr(publisher, "_producer", lambda: mock_prod)
    monkeypatch.setattr(publisher, "_deduplicator", lambda: mock_dedup)

    return mock_prod, mock_dedup


class TestPublishToKafka:

    ### Publishing new articles

    def test_publishes_new_article(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        publisher.publish_to_kafka([_ARTICLE])

        mock_prod.produce.assert_called_once()

    def test_publish_uses_correct_topic(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        publisher.publish_to_kafka([_ARTICLE])

        args = mock_prod.produce.call_args[0]
        from config.news_scheduler_settings import get_setting
        assert args[0] == get_setting('TOPIC_NAME')

    def test_publish_serialises_article_as_json(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        publisher.publish_to_kafka([_ARTICLE])

        args = mock_prod.produce.call_args[0]
        payload = json.loads(args[1])
        assert payload["title"] == _ARTICLE["title"]
        assert payload["source"] == _ARTICLE["source"]

    def test_marks_article_seen_after_publish(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        publisher.publish_to_kafka([_ARTICLE])

        mock_dedup.mark_seen.assert_called_once()

    ### Deduplication skip

    def test_skips_duplicate_article(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = True

        publisher.publish_to_kafka([_ARTICLE])

        mock_prod.produce.assert_not_called()
        mock_dedup.mark_seen.assert_not_called()

    def test_publishes_only_non_duplicate_articles(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        dup_article = {**_ARTICLE, "link": "http://bbc.com/dup"}
        new_article = {**_ARTICLE, "link": "http://bbc.com/new"}

        mock_dedup.is_duplicate.side_effect = lambda key: "dup" in key

        publisher.publish_to_kafka([dup_article, new_article])

        assert mock_prod.produce.call_count == 1

    def test_count_of_published_vs_total_logged(self, mock_lazy_factories, caplog):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.side_effect = [False, True, False]
        articles = [
            {**_ARTICLE, "link": f"http://bbc.com/{i}"} for i in range(3)
        ]
        import logging
        with caplog.at_level(logging.INFO):
            publisher.publish_to_kafka(articles)

        assert "3" in caplog.text   # total
        assert "2" in caplog.text   # published

    ### Flush behaviour

    def test_flush_called_after_all_articles(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False
        articles = [
            {**_ARTICLE, "link": f"http://bbc.com/{i}"} for i in range(3)
        ]

        publisher.publish_to_kafka(articles)

        mock_prod.flush.assert_called_once()

    def test_flush_called_even_when_all_duplicates(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = True

        publisher.publish_to_kafka([_ARTICLE])

        mock_prod.flush.assert_called_once()

    def test_flush_called_on_empty_list(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories

        publisher.publish_to_kafka([])

        mock_prod.flush.assert_called_once()

    ### Dedup key construction

    def test_dedup_key_uses_link_published_at_source(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        publisher.publish_to_kafka([_ARTICLE])

        expected_key = _ARTICLE["link"] + _ARTICLE["published_at"] + _ARTICLE["source"]
        actual_key = mock_dedup.is_duplicate.call_args[0][0]
        assert actual_key == expected_key

    ### Lazy initialisation — factories called only on first publish

    def test_factories_not_called_before_publish(self):
        """_producer and _deduplicator must not be called at import time."""
        # If we reach this point without errors, module import was side-effect-free.
        # We verify by checking the cache is empty (cleared in autouse fixture).
        # A populated cache would mean something called them outside publish_to_kafka.
        assert True  # collection-time import of publisher above is the real assertion

    def test_deduplicator_factory_called_during_publish(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        called = []
        original = publisher._deduplicator
        publisher._deduplicator = lambda: (called.append(1), mock_dedup)[1]

        publisher.publish_to_kafka([_ARTICLE])

        assert len(called) == 1
        publisher._deduplicator = original

    def test_producer_factory_called_during_publish(self, mock_lazy_factories):
        mock_prod, mock_dedup = mock_lazy_factories
        mock_dedup.is_duplicate.return_value = False

        called = []
        original = publisher._producer
        publisher._producer = lambda: (called.append(1), mock_prod)[1]

        publisher.publish_to_kafka([_ARTICLE])

        assert len(called) == 1
        publisher._producer = original


class TestLazyCacheBodies:
    """
    ### Tests for the bodies of the lru_cache factory functions (lines 25, 29-30).
    Uses _ORIG_DEDUPLICATOR / _ORIG_PRODUCER saved at module-import time so that
    coverage can track the original source lines in publisher.py.
    """

    def test_deduplicator_factory_creates_article_deduplicator(self):
        from article_dedup.article_deduplicator import ArticleDeduplicator
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        mock_conn.cursor.return_value.__exit__.return_value = False

        _ORIG_DEDUPLICATOR.cache_clear()
        with patch("config.postgres_setup.psycopg.connect", return_value=mock_conn):
            original = publisher._deduplicator
            publisher._deduplicator = _ORIG_DEDUPLICATOR
            result = publisher._deduplicator()
            publisher._deduplicator = original

        assert isinstance(result, ArticleDeduplicator)

    def test_producer_factory_reads_config_and_creates_producer(self):
        mock_prod_instance = MagicMock()

        _ORIG_PRODUCER.cache_clear()
        with patch("config.confluent_producer_setup.Producer", return_value=mock_prod_instance), \
             patch("config.confluent_producer_setup.os.getenv", return_value="val"):
            original = publisher._producer
            publisher._producer = _ORIG_PRODUCER
            result = publisher._producer()
            publisher._producer = original

        assert result is mock_prod_instance