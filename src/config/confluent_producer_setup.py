"""
@Author: Srini Yedluri
@Date: 3/26/26
@Time: 11:10 AM
@File: confluent_producer_setup.py
"""
import os

from confluent_kafka import Producer

def get_producer(config):
  """
  Creates Producer based on configuration provided and
  secrets information from environment variables
  :param config:
  :return: Producer
  """
  return Producer({**config})