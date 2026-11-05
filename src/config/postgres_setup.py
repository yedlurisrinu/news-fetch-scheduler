import psycopg
import os
from typing import Any

from psycopg import Connection
from pathlib import Path

from config.news_scheduler_settings import get_setting

def instantiate_connection() -> Connection:
    """Creating PostgreSQL connection that is running in local docker """
    return psycopg.connect(dbname=os.getenv("POSTGRES_DB"),
                           user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"),
                           connect_timeout=get_setting('DB_CONNECT_TIMEOUT_SECONDS'),
                           **load_config())

def load_config() -> dict[str, Any]:
    path = Path(__file__).parent.parent
    with open(str(path)+'/resources/postgers.properties') as config:
        lines = config.readlines()
    props: dict[str, Any] = {}
    for line in lines:
        if not line.startswith('#'):
            keyVal = line.split('=')
            props[keyVal[0].strip()] = keyVal[1].strip()
    return props


