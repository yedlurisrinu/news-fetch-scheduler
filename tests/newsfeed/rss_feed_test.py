"""
### Unit tests for src/newsfeed/rss_feed.py
Tests RSS feed fetching, article mapping, date parsing, and per-feed error isolation.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from newsfeed.rss_feed import fetch_rss_articles, _parse_date


def _make_entry(title="Headline", summary="Summary text", link="http://example.com",
                published="Tue, 17 Mar 2026 21:39:17 +0000", pub_date=None):
    """Build a feedparser-style entry object."""
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": title,
        "summary": summary,
        "link": link,
        "published": published,
        "pubDate": pub_date or "",
    }.get(key, default)
    entry.title = title
    entry.summary = summary
    entry.link = link
    if published:
        entry.published = published
        # hasattr returns True for 'published'
        entry.__class__ = type("Entry", (), {
            "published": published,
            "get": entry.get,
        })
    return entry


def _make_feed(entries):
    feed = MagicMock()
    feed.entries = entries
    return feed


class TestFetchRssArticles:

    ### Happy path

    def test_returns_list_of_dicts(self):
        entry = _make_entry()
        with patch("newsfeed.rss_feed.feedparser.parse", return_value=_make_feed([entry])):
            result = fetch_rss_articles()
        assert isinstance(result, list)
        assert all(isinstance(a, dict) for a in result)

    def test_maps_fields_correctly(self):
        with patch("newsfeed.rss_feed.feedparser.parse") as mock_parse:
            entry = MagicMock()
            entry.get = lambda key, default="": {
                "title": "Test Title",
                "summary": "Test Summary",
                "link": "http://bbc.com/1",
                "published": "Tue, 17 Mar 2026 21:39:17 +0000",
            }.get(key, default)
            entry.published = "Tue, 17 Mar 2026 21:39:17 +0000"
            mock_parse.return_value = _make_feed([entry])

            result = fetch_rss_articles()

        # At least one article from each configured feed, but we only mocked one parse
        assert len(result) > 0
        first = result[0]
        assert first["title"] == "Test Title"
        assert first["summary"] == "Test Summary"
        assert first["link"] == "http://bbc.com/1"
        assert "source" in first
        assert "fetched_at" in first

    def test_aggregates_articles_from_all_feeds(self):
        entry = MagicMock()
        entry.get = lambda key, default="": default
        entry.published = "Tue, 17 Mar 2026 21:39:17 +0000"

        with patch("newsfeed.rss_feed.feedparser.parse") as mock_parse:
            mock_parse.return_value = _make_feed([entry, entry])  # 2 entries per feed
            result = fetch_rss_articles()

        from config.news_scheduler_settings import get_setting
        assert len(result) == 2 * len(get_setting('RSS_FEEDS'))

    ### Error isolation

    def test_skips_failed_feed_and_continues(self):
        entry = MagicMock()
        entry.get = lambda key, default="": default
        entry.published = "Tue, 17 Mar 2026 21:39:17 +0000"

        call_count = {"n": 0}

        def side_effect(url):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("timeout")
            return _make_feed([entry])

        with patch("newsfeed.rss_feed.feedparser.parse", side_effect=side_effect):
            result = fetch_rss_articles()

        # First feed failed, remaining feeds produced articles
        from config.news_scheduler_settings import get_setting
        assert len(result) == (len(get_setting('RSS_FEEDS')) - 1) * 1

    def test_returns_empty_list_when_all_feeds_fail(self):
        with patch("newsfeed.rss_feed.feedparser.parse", side_effect=Exception("all fail")):
            result = fetch_rss_articles()
        assert result == []


class TestParseDatePrivate:

    ### _parse_date helper

    def test_uses_published_field(self):
        entry = MagicMock(spec=["published", "get"])
        entry.get = lambda key, default="": "Tue, 17 Mar 2026 21:39:17 +0000" if key == "published" else default
        result = _parse_date(entry)
        assert "2026-03-17" in result

    def test_uses_pubdate_when_no_published(self):
        entry = MagicMock(spec=["pubDate", "get"])
        entry.get = lambda key, default="": "Wed, 18 Mar 2026 00:04:34 GMT" if key == "pubDate" else default
        result = _parse_date(entry)
        assert "2026-03-18" in result

    def test_falls_back_to_now_when_no_date_fields(self):
        entry = MagicMock(spec=[])  # no published or pubDate attributes
        before = datetime.now(timezone.utc)
        result = _parse_date(entry)
        after = datetime.now(timezone.utc)
        assert isinstance(result, str)
        assert "T" in result  # ISO format