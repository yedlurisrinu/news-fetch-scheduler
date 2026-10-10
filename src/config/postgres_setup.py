import psycopg
import os

from psycopg import Connection
from pathlib import Path
connection :Connection

def instantiate_connection():
    """Creating PostgreSQL connection that is running in local docker """
    return psycopg.connect(dbname=os.getenv("POSTGRES_DB"),
                           user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"),
                           **load_config())

def load_config():
    path = Path(__file__).parent.parent
    with open(str(path)+'/resources/postgers.properties') as config:
        lines = config.readlines()
    config = {}
    for line in lines:
        if not line.startswith('#'):
            keyVal = line.split('=')
            config[keyVal[0].strip()] = keyVal[1].strip()
    return config


print(load_config())