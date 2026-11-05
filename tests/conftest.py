"""
Root conftest.py — patches psycopg.connect and confluent_kafka.Producer before
test collection. publisher.py creates its connection and producer lazily (lru_cache
factories), so nothing connects at import time; these patches are a guard so that
no test can ever open a real Postgres connection or create a real Kafka producer.
"""

import atexit
from unittest.mock import MagicMock, patch

# Must start before test files are imported (i.e. at conftest import time)
_pg_patcher = patch("psycopg.connect", return_value=MagicMock())
_producer_patcher = patch("confluent_kafka.Producer", return_value=MagicMock())

_pg_patcher.start()
_producer_patcher.start()

atexit.register(_pg_patcher.stop)
atexit.register(_producer_patcher.stop)

import pytest

from config.news_scheduler_settings import load_setting


@pytest.fixture(scope="session", autouse=True)
def _load_settings() -> None:
    """main() calls load_setting() at startup; tests need the same settings loaded."""
    load_setting()
