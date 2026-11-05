import logging
import time
from pathlib import Path

import schedule

from config.news_scheduler_settings import get_setting
from newsfeed.fetch_all_articles import fetch_all_articles
from publisher.publisher import refresh_dedup_cache

logger = logging.getLogger(__name__)

# Touched every loop iteration; the Docker HEALTHCHECK checks its mtime.
HEARTBEAT_FILE = Path("/tmp/heartbeat")


def _run_fetch_job() -> None:
    """Runs one fetch; logs failures so the scheduler loop survives them."""
    try:
        fetch_all_articles()
    except Exception:
        logger.exception("[Scheduler] Fetch job failed")


def _run_dedup_refresh_job() -> None:
    """Daily dedup cache reload; logs failures so the scheduler loop survives them."""
    try:
        refresh_dedup_cache()
    except Exception:
        logger.exception("[Scheduler] Dedup cache refresh failed")


def schedule_fetch() -> None:
    """
    This function will call fetch all articles on startup and will
     schedule a job on the fetch_all_articles() in a configurable interval
     like every 30 min.
    """
    # Run fetch articles on start info
    _run_fetch_job()
    # Then schedule
    schedule.every(get_setting("SCHEDULER_INTERVAL_MINUTES")).minutes.do(_run_fetch_job)
    # daily, just after the date rolls over (container clock is UTC), so the window moves with CURRENT_DATE
    schedule.every().day.at(get_setting("DEDUP_REFRESH_AT")).do(_run_dedup_refresh_job)
    logger.info(
        f"[Scheduler] Starting — polling every {get_setting('SCHEDULER_INTERVAL_MINUTES')} mins, "
        f"dedup cache refresh daily at {get_setting('DEDUP_REFRESH_AT')}"
    )
    while True:
        schedule.run_pending()
        HEARTBEAT_FILE.touch()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(" Scheduler is running ... ")
        time.sleep(get_setting("SCHEDULER_SLEEP_SECONDS"))
