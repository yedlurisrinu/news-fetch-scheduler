"""
@Author: Srini Yedluri
@Date: 3/21/26
@File: main.py
"""
"""
The main module that loads config, calling common
 module for setup logging and loading secrets from
 vault server that is running in docker on localhost.
 After successful completion it will schedule a job to
 fetch articles information periodically.
"""
from config.logging_setup import setup_logging
# loads secretes from vault and set into environment variables
from config.vault_secrets import load_secrets
from scheduler import schedule_feed_fetch
from config.news_scheduler_settings import load_setting
def main():
    setup_logging()
    load_secrets()
    load_setting()
    schedule_feed_fetch.schedule_fetch()

main()