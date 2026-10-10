"""
### Unit tests for src/config/confluent_producer_setup.py
Tests that get_producer passes the correct environment variables and
merges the supplied config into the Producer constructor call.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from config.confluent_producer_setup import get_producer


class TestGetProducer:

    ### Environment variable injection

    def test_uses_env_var(self):
        env = {
            "bootstrap.servers": "kafka:9092",
            'security.protocol':'PLAINTEXT'
        }
        with patch("config.confluent_producer_setup.Producer") as mock_producer_cls:
             get_producer(env)
        kwargs = mock_producer_cls.call_args[0][0]
        assert kwargs["bootstrap.servers"] == "kafka:9092"
        assert kwargs["security.protocol"] == "PLAINTEXT"

    """Not relevant for local testing only when deployed to AWS"""
    def test_uses_sasl_credentials_from_env(self):
        env = {
            "sasl.username": "kafka_user",
            "sasl.password": "secret123",
        }
        with patch("config.confluent_producer_setup.Producer") as mock_producer_cls:
            get_producer(env)

        kwargs = mock_producer_cls.call_args[0][0]
        assert kwargs["sasl.username"] == "kafka_user"
        assert kwargs["sasl.password"] == "secret123"

    """Not relevant for local development but might be useful when deploying to AWS"""
    def test_uses_client_id_from_env(self):
        env = {
            "client.id": "news-scheduler",
        }
        with patch("config.confluent_producer_setup.Producer") as mock_producer_cls:
            get_producer(env)

        kwargs = mock_producer_cls.call_args[0][0]
        assert kwargs["client.id"] == "news-scheduler"

    ### Config merging

    def test_merges_extra_config_into_producer(self):
        extra = {"security.protocol": "SASL_SSL", "sasl.mechanisms": "PLAIN"}
        with patch("config.confluent_producer_setup.os.getenv", return_value="val"), \
             patch("config.confluent_producer_setup.Producer") as mock_producer_cls:
            get_producer(extra)

        kwargs = mock_producer_cls.call_args[0][0]
        assert kwargs["security.protocol"] == "SASL_SSL"
        assert kwargs["sasl.mechanisms"] == "PLAIN"

    def test_returns_producer_instance(self):
        mock_instance = MagicMock()
        with patch("config.confluent_producer_setup.os.getenv", return_value="val"), \
             patch("config.confluent_producer_setup.Producer", return_value=mock_instance):
            result = get_producer({})

        assert result is mock_instance