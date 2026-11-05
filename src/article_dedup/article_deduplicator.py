import datetime
import hashlib
import logging

from psycopg import Connection

from config.news_scheduler_settings import get_setting

logger = logging.getLogger(__name__)


class ArticleDeduplicator:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self.local_cache: set[str] = set()  # fast O(1) lookups
        self._warm_cache()

    def _load(self) -> set[str]:
        """Article ID hashes from today and the previous DEDUP_WINDOW_DAYS full days.

        created_at is a DATE, so the window is compared in whole days: comparing it with
        NOW() - n days would drop every row from the oldest day (stored as midnight)."""
        with self.conn.cursor() as cur:
            cur.execute(
                """ SELECT ARTICLE_ID_HASH FROM NEWS_ARTICLE_IDS WHERE CREATED_AT >= CURRENT_DATE - %s::integer""",
                (get_setting("DEDUP_WINDOW_DAYS"),),
            )
            rows = cur.fetchall()
        return {row[0] for row in rows}

    def _warm_cache(self) -> None:
        """Startup load; a failure here is fatal (the caller cannot dedup without it)."""
        logger.info("Warming cache from database...")
        self.local_cache = self._load()
        logger.info(f"Cache warmed with {len(self.local_cache)} article IDs")

    def refresh(self) -> None:
        """Reload the cache from the DB window (run daily): keeps memory bounded and makes a
        long-running process dedup like a freshly started one.

        Load first, then swap: on any error the current cache is kept (an empty cache would
        re-publish the whole window), and the next scheduled refresh tries again."""
        try:
            fresh = self._load()
        except Exception:
            logger.exception(
                f"Dedup cache refresh failed; keeping the current {len(self.local_cache)} article IDs"
            )
            return
        dropped = len(self.local_cache - fresh)
        self.local_cache = fresh
        logger.info(
            f"Dedup cache refreshed: {len(fresh)} article IDs ({dropped} older than the window dropped)"
        )

    def _hash(self, article_id: str) -> str:
        return hashlib.md5(article_id.encode()).hexdigest()

    def is_duplicate(self, article_id: str) -> bool:
        """Check local cache first — avoids DB hit on every article"""
        return self._hash(article_id) in self.local_cache

    def mark_seen(self, article_id: str) -> None:
        """Write the new article to both DB and local cache"""
        id_hash = self._hash(article_id)

        # Write to DB
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO news_article_ids(article_id_hash, created_at)
                VALUES (%s,%s)
                ON CONFLICT DO NOTHING
            """,
                (id_hash, datetime.datetime.now(datetime.UTC)),
            )
            self.conn.commit()
        # Write to local cache
        self.local_cache.add(id_hash)
