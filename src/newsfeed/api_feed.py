import os
from typing import Any

import httpx
from datetime import datetime, timezone
from config.news_scheduler_settings import get_setting
import logging
from common.article import Article
from common.http_client import http_client

logger = logging.getLogger(__name__)
def fetch_api_articles() -> list[dict[str, Any]]:
    """
        The function is responsible for fetching article information from APIs, parsing
        and creating model object.
        This needs NEWS_API_KEY be available in the environment, which will be loaded
        at application startup from vault server
        :return: list of Articles as dictionaries
        """
    articles = []
    try:
        response = http_client().get(get_setting('NEWS_API_URL'),
                                     params=get_setting('NEWS_API_PARAMS'),
                                     headers={"X-Api-Key": os.getenv('NEWS_API_KEY', '')})
        response.raise_for_status()

        data = response.json()
        for item in data.get("articles", []):
            article_meta = {
                "title":      item.get("title", ""),
                "summary":    item.get("description", ""), # content
                "link":       item.get("url", ""),
                "published_at":  item.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                "source":     item.get("source", {}).get("name", "NewsAPI"),
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }

            articles.append(Article(**article_meta).model_dump())
        logger.info(f"[API] Fetched {len(articles)} articles")
    except httpx.HTTPStatusError as e:
        logger.warning(f"[API] Failed to fetch articles: HTTP {e.response.status_code}")
    except httpx.HTTPError as e:
        logger.warning(f"[API] Failed to fetch articles: {type(e).__name__}")
    except Exception:
        logger.exception("[API] Failed to fetch articles")
    return articles

