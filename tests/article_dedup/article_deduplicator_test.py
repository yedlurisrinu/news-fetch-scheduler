"""
### Unit tests for src/article_dedup/article_deduplicator.py
Tests cache warm-up, duplicate detection, and mark-seen logic
using a fully mocked psycopg connection.
"""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from article_dedup.article_deduplicator import ArticleDeduplicator


def _md5(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()


@pytest.fixture
def mock_conn():
    """Returns a MagicMock that mimics a psycopg connection with cursor context manager."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return conn, cursor


class TestWarmCache:
    ### Cache warm-up on init

    def test_warm_cache_populates_local_cache(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("hash_a",), ("hash_b",), ("hash_c",)]

        dedup = ArticleDeduplicator(conn)

        assert dedup.local_cache == {"hash_a", "hash_b", "hash_c"}

    def test_warm_cache_empty_db(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dedup = ArticleDeduplicator(conn)

        assert dedup.local_cache == set()

    def test_warm_cache_executes_correct_query(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        ArticleDeduplicator(conn)

        executed_sql = cursor.execute.call_args[0][0]
        assert "NEWS_ARTICLE_IDS" in executed_sql
        assert (
            "CURRENT_DATE - %s::integer" in executed_sql
        )  # whole days: created_at is a DATE
        from config.news_scheduler_settings import get_setting

        assert cursor.execute.call_args[0][1] == (get_setting("DEDUP_WINDOW_DAYS"),)


class TestIsDuplicate:
    ### Duplicate detection via local cache

    def test_returns_true_for_known_article(self, mock_conn):
        conn, cursor = mock_conn
        article_id = "http://example.com/article2026-03-28BBC"
        expected_hash = _md5(article_id)
        cursor.fetchall.return_value = [(expected_hash,)]

        dedup = ArticleDeduplicator(conn)

        assert dedup.is_duplicate(article_id) is True

    def test_returns_false_for_unknown_article(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dedup = ArticleDeduplicator(conn)

        assert dedup.is_duplicate("new_unseen_article_key") is False

    def test_uses_md5_hash_for_comparison(self, mock_conn):
        conn, cursor = mock_conn
        raw_id = "some_key"
        cursor.fetchall.return_value = [(_md5(raw_id),)]

        dedup = ArticleDeduplicator(conn)

        assert dedup.is_duplicate(raw_id) is True
        # A different key with the same prefix should not match
        assert dedup.is_duplicate(raw_id + "_extra") is False


class TestMarkSeen:
    ### Writing to DB and local cache

    def test_mark_seen_adds_to_local_cache(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dedup = ArticleDeduplicator(conn)
        dedup.mark_seen("new_article_key")

        assert _md5("new_article_key") in dedup.local_cache

    def test_mark_seen_inserts_into_db(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dedup = ArticleDeduplicator(conn)
        dedup.mark_seen("new_article_key")

        # cursor.execute called twice: once in _warm_cache, once in mark_seen
        assert cursor.execute.call_count == 2
        insert_call_args = cursor.execute.call_args_list[1]
        sql = insert_call_args[0][0]
        assert "INSERT INTO news_article_ids" in sql
        assert "ON CONFLICT DO NOTHING" in sql

    def test_mark_seen_commits_transaction(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dedup = ArticleDeduplicator(conn)
        dedup.mark_seen("article_key")

        conn.commit.assert_called_once()

    def test_mark_seen_then_is_duplicate(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dedup = ArticleDeduplicator(conn)
        dedup.mark_seen("article_key")

        assert dedup.is_duplicate("article_key") is True


class TestRefresh:
    def test_refresh_replaces_cache_with_db_window(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("old-1",), ("keep",)]
        dedup = ArticleDeduplicator(conn)
        dedup.local_cache.add("marked-in-memory")

        cursor.fetchall.return_value = [("keep",), ("new-1",)]
        dedup.refresh()

        assert dedup.local_cache == {"keep", "new-1"}

    def test_failed_refresh_keeps_current_cache(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("a",), ("b",)]
        dedup = ArticleDeduplicator(conn)

        cursor.execute.side_effect = RuntimeError("connection lost")
        with patch("article_dedup.article_deduplicator.logger") as logger:
            dedup.refresh()  # must not raise

        assert dedup.local_cache == {"a", "b"}
        logger.exception.assert_called_once()
