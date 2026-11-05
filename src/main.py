"""Entry point: set up logging, load secrets from Vault and settings from the TOML file,
then run the fetch job now and every SCHEDULER_INTERVAL_MINUTES (blocking loop)."""
from config.logging_setup import setup_logging
from config.vault_secrets import load_secrets
from scheduler import schedule_feed_fetch
from config.news_scheduler_settings import load_setting
def main() -> None:
    setup_logging()
    load_secrets()
    load_setting()
    schedule_feed_fetch.schedule_fetch()

if __name__ == "__main__":
    main()
