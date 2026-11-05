"""
tests/config/startup_test.py

Start-up code without live services:
  - load_secrets: required env vars, Vault auth failure, secrets injected, read failure wrapped
  - setup_logging: dictConfig from resources (daily rotating file handler), fallback on a bad file
  - load_setting: a missing settings file is logged and re-raised
  - main: start-up order
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

VAULT_ENV = {
    "VAULT_ADDR": "http://vault-server:8200",
    "VAULT_TOKEN": "tok",
    "VAULT_SECRET_PATH": "secret/CREDENTIALS",
}


class TestLoadSecrets:
    def test_missing_addr_or_token_raises(self, monkeypatch):
        from config.vault_secrets import load_secrets

        monkeypatch.delenv("VAULT_ADDR", raising=False)
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        with pytest.raises(ValueError, match="VAULT_ADDR and VAULT_TOKEN"):
            load_secrets()

    def test_missing_secret_path_raises(self, monkeypatch):
        from config.vault_secrets import load_secrets

        monkeypatch.setenv("VAULT_ADDR", VAULT_ENV["VAULT_ADDR"])
        monkeypatch.setenv("VAULT_TOKEN", "tok")
        monkeypatch.delenv("VAULT_SECRET_PATH", raising=False)
        with pytest.raises(ValueError, match="VAULT_SECRET_PATH"):
            load_secrets()

    def test_auth_failure_raises(self, monkeypatch):
        from config.vault_secrets import load_secrets

        for k, v in VAULT_ENV.items():
            monkeypatch.setenv(k, v)
        client = MagicMock()
        client.is_authenticated.return_value = False
        with (
            patch("config.vault_secrets.Client", return_value=client),
            pytest.raises(ValueError, match="authentication failed"),
        ):
            load_secrets()

    def test_success_injects_env(self, monkeypatch):
        from config.vault_secrets import load_secrets

        for k, v in VAULT_ENV.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv("INJECTED_KEY", raising=False)
        client = MagicMock()
        client.is_authenticated.return_value = True
        client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"INJECTED_KEY": "value"}}
        }
        with patch("config.vault_secrets.Client", return_value=client):
            load_secrets()
        assert os.environ["INJECTED_KEY"] == "value"
        assert client.secrets.kv.v2.read_secret_version.call_args.kwargs == {
            "path": "CREDENTIALS",
            "mount_point": "secret",
        }
        monkeypatch.delenv("INJECTED_KEY")

    def test_read_failure_is_wrapped_without_details(self, monkeypatch):
        from config.vault_secrets import load_secrets

        for k, v in VAULT_ENV.items():
            monkeypatch.setenv(k, v)
        client = MagicMock()
        client.is_authenticated.return_value = True
        client.secrets.kv.v2.read_secret_version.side_effect = PermissionError(
            "vault-server:8200 says no"
        )
        with (
            patch("config.vault_secrets.Client", return_value=client),
            pytest.raises(ValueError) as exc,
        ):
            load_secrets()
        assert "PermissionError" in str(exc.value) and "vault-server" not in str(
            exc.value
        )
        assert isinstance(exc.value.__cause__, PermissionError)


class TestSetupLogging:
    def test_loads_dict_config_from_resources(self):
        from config.logging_setup import setup_logging

        with patch("config.logging_setup.logging.config.dictConfig") as dict_config:
            setup_logging()
        (config,), _ = dict_config.call_args
        assert (
            config["handlers"]["file"]["class"]
            == "logging.handlers.TimedRotatingFileHandler"
        )

    def test_bad_file_falls_back_to_basic_config(self):
        from config.logging_setup import setup_logging

        with (
            patch("config.logging_setup.logging.basicConfig") as basic,
            patch("config.logging_setup.logger") as logger,
        ):
            setup_logging("does-not-exist.json")
        basic.assert_called_once_with(level=logging.INFO)
        logger.exception.assert_called_once()


class TestLoadSetting:
    def test_missing_settings_file_is_logged_and_raised(self):
        from config import news_scheduler_settings

        with (
            patch(
                "builtins.open",
                side_effect=FileNotFoundError("app-config-settings.toml"),
            ),
            patch.object(news_scheduler_settings, "logger") as logger,
            pytest.raises(FileNotFoundError),
        ):
            news_scheduler_settings.load_setting()
        logger.exception.assert_called_once()


class TestMain:
    def test_start_up_order(self):
        import main

        calls = MagicMock()
        with (
            patch.object(main, "setup_logging", calls.setup_logging),
            patch.object(main, "load_secrets", calls.load_secrets),
            patch.object(main, "load_setting", calls.load_setting),
            patch.object(main, "schedule_feed_fetch", calls.schedule_feed_fetch),
        ):
            main.main()
        assert [c[0] for c in calls.mock_calls] == [
            "setup_logging",
            "load_secrets",
            "load_setting",
            "schedule_feed_fetch.schedule_fetch",
        ]
