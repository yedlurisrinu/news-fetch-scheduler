from typing import Any

from confluent_kafka import Producer


def get_producer(config: dict[str, Any]) -> Producer:
    """
    Creates the Kafka Producer from the settings read from
    resources/kafka-client.properties (bootstrap servers, client tuning)
    :param config:
    :return: Producer
    """
    return Producer({**config})
