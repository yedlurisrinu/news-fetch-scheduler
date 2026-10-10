"""
@Author: Srini Yedluri
@Date: 3/25/26
@Time: 6:27 PM
@File: publisher.py
"""
from functools import lru_cache
from pathlib import Path

from common.utils import generate_id
from article_dedup.article_deduplicator import ArticleDeduplicator
from config.postgres_setup import instantiate_connection
from confluent_kafka import Producer
import json
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

def publish_to_kafka(articles: list[dict]):
    """This function is responsible for publishing article to
    conflent kafka after doing dedup check against warm inmemory cache """
    dedup = _deduplicator()
    prod  = _producer()
    published_count = 0
    for article in articles:
        key =  article["link"]+ article['published_at'] + article['source']
        if not dedup.is_duplicate(key):
            published_count += 1
            prod.produce(get_setting('TOPIC_NAME'), json.dumps(article), generate_id(key))
            dedup.mark_seen(key)
            logger.debug(f"Produced messages to topic {get_setting('TOPIC_NAME')}: key = {key:12}")

    # send any outstanding or buffered messages to the Kafka broker
    prod.flush()
    logger.info(f"[Kafka] Total {len(articles)} articles, Published {published_count} articles after dedup")