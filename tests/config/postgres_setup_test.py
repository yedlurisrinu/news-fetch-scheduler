"""
### Unit tests for src/config/postgres_setup.py
Tests that instantiate_connection passes the correct env-var-sourced
parameters to psycopg.connect and returns the connection object.
"""
import pytest
from unittest.mock import MagicMock, patch

from config.postgres_setup import instantiate_connection


_ENV = {
    "host": "db-host",
    "dbname": "news_db",
    "user": "news_user",
    "password": "s3cr3t",
    "port": "5432",
    'POSTGRES_DB':'news_db',
    'POSTGRES_USER':'news_user',
    'POSTGRES_PASSWORD':'s3cr3t'
}


class TestInstantiateConnection:

    ### Connection parameter mapping

    def test_passes_host_from_env(self):
        with patch("config.postgres_setup.psycopg.connect") as mock_connect, \
             patch("config.postgres_setup.os.getenv", side_effect=lambda k: _ENV.get(k)), \
             patch("config.postgres_setup.load_config") as load:
            load.return_value = {"host": "db-host","port": "5432"}
            instantiate_connection()

        assert mock_connect.call_args[1]["host"] == "db-host"

    def test_passes_dbname_from_env(self):
        with patch("config.postgres_setup.psycopg.connect") as mock_connect: 
            with patch("config.postgres_setup.os.getenv", side_effect=lambda k: _ENV.get(k)),\
            patch("config.postgres_setup.load_config") as load:
                load.return_value = {"host": "db-host","port": "5432"}
                instantiate_connection()

        assert mock_connect.call_args[1]["dbname"] == "news_db"

    def test_passes_user_from_env(self):
        with patch("config.postgres_setup.psycopg.connect") as mock_connect, \
             patch("config.postgres_setup.os.getenv", side_effect=lambda k: _ENV.get(k)), \
             patch("config.postgres_setup.load_config") as load:
             load.return_value = {"host": "db-host","port": "5432"}
             instantiate_connection()

        assert mock_connect.call_args[1]["user"] == "news_user"

    def test_passes_password_from_env(self):
        with patch("config.postgres_setup.psycopg.connect") as mock_connect, \
             patch("config.postgres_setup.os.getenv", side_effect=lambda k: _ENV.get(k)), \
             patch("config.postgres_setup.load_config") as load:
             load.return_value = {"host": "db-host","port": "5432"}
             instantiate_connection()

        assert mock_connect.call_args[1]["password"] == "s3cr3t"

    def test_passes_port_from_env(self):
        with patch("config.postgres_setup.psycopg.connect") as mock_connect, \
             patch("config.postgres_setup.os.getenv", side_effect=lambda k: _ENV.get(k)), \
             patch("config.postgres_setup.load_config") as load:
             load.return_value = {"host": "db-host","port": "5432"}
             instantiate_connection()

        assert mock_connect.call_args[1]["port"] == "5432"

    ### Return value

    def test_returns_connection_object(self):
        mock_conn = MagicMock()
        with patch("config.postgres_setup.psycopg.connect", return_value=mock_conn), \
             patch("config.postgres_setup.os.getenv", side_effect=lambda k: _ENV.get(k)), \
             patch("config.postgres_setup.load_config") as load:
             load.return_value = {"host": "db-host","port": "5432"}
             result = instantiate_connection()

        assert result is mock_conn

    ### Missing env vars

    def test_passes_none_when_env_var_missing(self):
        with patch("config.postgres_setup.psycopg.connect") as mock_connect, \
             patch("config.postgres_setup.os.getenv", return_value=None), \
             patch("config.postgres_setup.load_config") as load:
             load.return_value = {'host':None, 'port':None}
             instantiate_connection()

        kwargs = mock_connect.call_args[1]
        assert kwargs["host"] is None
        assert kwargs["password"] is None