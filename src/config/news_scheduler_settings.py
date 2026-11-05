import logging
from pathlib import Path
from tomllib import load
from typing import Any

"""General Static information"""
logger = logging.getLogger(__name__)
setting_config: dict[str, Any] = {}


def get_setting(key: str) -> Any:
    return setting_config[key]


def load_setting() -> None:
    global setting_config
    path = Path(__file__).parent.parent
    try:
        with open(
            file=str(path) + "/resources/app-config-settings.toml", mode="rb"
        ) as config:
            setting_config = load(config)
    except FileNotFoundError:
        logger.exception(" Exception while loading client properties")
        raise
