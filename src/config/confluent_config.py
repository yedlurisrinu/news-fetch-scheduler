import logging

logger = logging.getLogger(__name__)


def read_config(client_properties: str) -> dict[str, str]:
    """
    Reads confluent Kafka configuration from properties file
    :param client_properties:
    :return: dictionary
    """
    config: dict[str, str] = {}
    try:
        with open(client_properties) as fh:
            for line in fh:
                line = line.strip()
                if len(line) != 0 and line[0] != "#":
                    parameter, value = line.strip().split("=", 1)
                    config[parameter] = value.strip()
    except FileNotFoundError:
        logger.exception(" Exception while loading client properties")
        raise
    return config
