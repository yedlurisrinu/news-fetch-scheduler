"""
@Author: Srini Yedluri
@Date: 3/25/26
@Time: 6:33 PM
@File: schedule_feed_fetch.py
"""
import time
import schedule
import logging
from config.news_scheduler_settings import get_setting
from newsfeed.fetch_all_articles import fetch_all_articles
logger = logging.getLogger(__name__)

def schedule_fetch():
    """
    This function will call fetch all articles on startup and will
     schedule a job on the fetch_all_articles() in a configurable interval
     like every 30 min.
    """
    # Run fetch articles on start info
    fetch_all_articles()
    # Then schedule
    schedule.every(get_setting('SCHEDULER_INTERVAL_MINUTES')).minutes.do(fetch_all_articles)
    logger.info(f"[Scheduler] Starting — polling every {get_setting('SCHEDULER_INTERVAL_MINUTES')} mins")
    while True:
        schedule.run_pending()
        if logger.level == logging.DEBUG:
            logger.debug(" Scheduler is running ... ")
        time.sleep(5)

