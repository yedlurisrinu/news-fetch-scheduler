import feedparser
import httpx
from typing import Any

from datetime import datetime, timezone
from common.utils import parse_to_iso
from common.article import Article
from common.http_client import http_client
from config.news_scheduler_settings import get_setting
import logging

logger = logging.getLogger(__name__)

def fetch_rss_articles() -> list[dict[str, Any]]:
    """
    The function is responsible for fetching article information from rss
    feeds, parsing and creating model object.
    :return: list of Articles as dictionaries
    """
    articles = []
    for feed_config in get_setting('RSS_FEEDS'):
        try:
            response = http_client().get(feed_config["url"])
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                article_meta = {
                    "title":       entry.get("title", ""),
                    "summary":     entry.get("summary", ""),
                    "link":        entry.get("link", ""),
                    "published_at":  _parse_date(entry),
                    "source":      feed_config["name"],
                    "fetched_at":  datetime.now(timezone.utc).isoformat()
                }
                articles.append(Article(**article_meta).model_dump())
        except httpx.HTTPStatusError as e:
            # expected feed failures (down, blocked, bad status): one line, no traceback
            logger.warning(f"[RSS] Failed to fetch {feed_config['name']}: HTTP {e.response.status_code}")
        except httpx.HTTPError as e:
            logger.warning(f"[RSS] Failed to fetch {feed_config['name']}: {type(e).__name__}: {e}")
        except Exception:
            logger.exception(f"[RSS] Failed to process {feed_config['name']}")

    logger.info(f"[RSS] Fetched {len(articles)} articles")
    return articles

def _parse_date(entry: Any) -> str:
    if hasattr(entry, "published"):
        return parse_to_iso(entry.get("published"))
    if hasattr(entry, "pubDate"):
        return parse_to_iso(entry.get("pubDate"))
    return datetime.now(timezone.utc).isoformat()