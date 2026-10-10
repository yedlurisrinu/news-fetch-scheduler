import feedparser

from datetime import datetime, timezone
from common.utils import parse_to_iso
from common.article import Article
from config.news_scheduler_settings import get_setting
import logging

logger = logging.getLogger(__name__)

def fetch_rss_articles() -> list[dict]:
    """
    The function is responsible for fetching article information from rss
    feeds, parsing and creating model object.
    :return: list of Articles as dictionaries
    """
    articles = []
    for feed_config in get_setting('RSS_FEEDS'):
        try:
            feed = feedparser.parse(feed_config["url"])
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
        except Exception as e:
            logger.error(f"[RSS] Failed to fetch {feed_config['name']}: {e}",exc_info=True )

    logger.info(f"[RSS] Fetched {len(articles)} articles")
    return articles

def _parse_date(entry) -> str:
    if hasattr(entry, "published"):
        return parse_to_iso(entry.get("published"))
    if hasattr(entry, "pubDate"):
        return parse_to_iso(entry.get("pubDate"))
    return datetime.now(timezone.utc).isoformat()