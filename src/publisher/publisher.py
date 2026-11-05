from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from common.utils import generate_id
from article_dedup.article_deduplicator import ArticleDeduplicator
from config.postgres_setup import instantiate_connection
from confluent_kafka import KafkaError, Message, Producer
import json
import psycopg
import logging
from config.confluent_config import read_config
from config.confluent_producer_setup import get_producer
from config.news_scheduler_settings import get_setting

BASE_PATH = str(Path(__file__).parent.parent)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=None)
def _deduplicator() -> ArticleDeduplicator:
    return ArticleDeduplicator(instantiate_connection())

@lru_cache(maxsize=None)
def _producer() -> Producer:
    kafka_config = read_config(BASE_PATH + "/resources/kafka-client.properties")
    return get_producer(kafka_config)

def _mark_seen(key: str) -> None:
    """Records the key in the dedup store, always through the current (cached) deduplicator.

    On a dropped DB connection: close it, build one new deduplicator (new connection, cache
    re-warmed) and retry once. Later calls use that new one, so a run reconnects at most once
    per drop. Never raises: it runs inside the Kafka delivery callback, and an exception there
    would abort flush(). An article left unmarked is simply re-sent next run (the ingester's
    _id makes that idempotent)."""
    dedup = _deduplicator()
    try:
        dedup.mark_seen(key)
        return
    except psycopg.OperationalError:
        logger.warning("[Dedup] Database connection lost, reconnecting once")
        try:
            dedup.conn.close()
        except Exception:  # noqa: BLE001 - the connection is already broken
            pass
        _deduplicator.cache_clear()
    try:
        _deduplicator().mark_seen(key)
    except Exception:
        logger.exception("[Dedup] Could not mark article as seen; it will be re-sent next run")

def refresh_dedup_cache() -> None:
    """Reload the current deduplicator's in-memory cache from the DB window (daily job)."""
    _deduplicator().refresh()

def publish_to_kafka(articles: list[dict[str, Any]]) -> None:
    """This function is responsible for publishing article to
    conflent kafka after doing dedup check against warm inmemory cache.
    An article is marked seen only after Kafka confirms delivery."""
    prod  = _producer()
    published_count = 0
    produced: set[str] = set()  # keys sent this run; delivery (and mark_seen) is asynchronous

    def delivery_callback(key: str) -> Callable[[KafkaError | None, Message], None]:
        def on_delivery(err: KafkaError | None, msg: Message) -> None:
            nonlocal published_count
            if err is not None:
                logger.error(f"[Kafka] Delivery failed for key = {key[:60]}: {err}")
                return
            published_count += 1
            _mark_seen(key)
        return on_delivery

    for article in articles:
        key =  article["link"]+ article['published_at'] + article['source']
        if key not in produced and not _deduplicator().is_duplicate(key):
            produced.add(key)
            prod.produce(get_setting('TOPIC_NAME'), json.dumps(article), generate_id(key),
                         on_delivery=delivery_callback(key))
            prod.poll(0)
            logger.debug(f"Produced messages to topic {get_setting('TOPIC_NAME')}: key = {key:12}")

    # send any outstanding or buffered messages to the Kafka broker
    remaining = prod.flush(get_setting('KAFKA_FLUSH_TIMEOUT_SECONDS'))
    if remaining > 0:
        logger.warning(f"[Kafka] {remaining} messages not delivered before flush timeout")
    logger.info(f"[Kafka] Total {len(articles)} articles, Published {published_count} articles after dedup")
