import hashlib
import logging
import datetime
logger = logging.getLogger(__name__)

class ArticleDeduplicator:

    def __init__(self, conn):
        self.conn = conn
        self.local_cache = set()  # fast O(1) lookups
        self._warm_cache()

    def _warm_cache(self):
        """Load last 2 days of article IDs into local cache on startup from PostgreSQL"""
        logger.info("Warming cache from database...")

        with self.conn.cursor() as cur:
            cur.execute(""" SELECT ARTICLE_ID_HASH FROM NEWS_ARTICLE_IDS WHERE CREATED_AT >= NOW() - INTERVAL '2 days'""")
            rows = cur.fetchall()
            self.local_cache = {row[0] for row in rows}

        logger.info(f"Cache warmed with {len(self.local_cache)} article IDs")

    def _hash(self, article_id):
        return hashlib.md5(article_id.encode()).hexdigest()

    def is_duplicate(self, article_id):
        """Check local cache first — avoids DB hit on every article"""
        return self._hash(article_id) in self.local_cache

    def mark_seen(self, article_id):
        """Write the new article to both DB and local cache """
        id_hash = self._hash(article_id)

        # Write to DB
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO news_article_ids(article_id_hash, created_at)
                VALUES (%s,%s)
                ON CONFLICT DO NOTHING
            """, (id_hash,datetime.datetime.now(datetime.timezone.utc)))
            self.conn.commit()
# TODO make datetime UTC
        # Write to local cache
        self.local_cache.add(id_hash)