"""
### Unit tests for src/scheduler/schedule_feed_fetch.py
Tests immediate execution, job registration, and polling loop behaviour.
The infinite while-loop is short-circuited by having time.sleep raise KeyboardInterrupt.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from scheduler.schedule_feed_fetch import schedule_fetch


class TestScheduleFetch:

    ### Immediate execution

    def test_calls_fetch_all_articles_immediately(self):
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles") as mock_fetch, \
             patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule, \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_fetch.assert_called()
        # First call must happen before the loop (immediate run)
        assert mock_fetch.call_count >= 1

    ### Job registration

    def test_registers_recurring_schedule(self):
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles"), \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt), \
             patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule:
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_schedule.every.assert_called_once()

    def test_schedule_interval_matches_settings(self):
        from config.news_scheduler_settings import get_setting
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles"), \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt), \
             patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule:
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_schedule.every.assert_called_once_with(get_setting('SCHEDULER_INTERVAL_MINUTES'))

    def test_do_registers_fetch_all_articles_as_job(self):
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles") as mock_fetch, \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt), \
             patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule:
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        # schedule.every(...).minutes.do(fetch_all_articles)
        do_call = mock_schedule.every.return_value.minutes.do
        do_call.assert_called_once_with(mock_fetch)

    ### Polling loop

    def test_run_pending_called_in_loop(self):
        call_count = {"n": 0}

        def sleep_side_effect(seconds):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise KeyboardInterrupt

        with patch("scheduler.schedule_feed_fetch.fetch_all_articles"), \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=sleep_side_effect), \
             patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule:
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        assert mock_schedule.run_pending.call_count >= 2

    def test_sleep_duration_is_5_seconds(self):
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles"), \
             patch("scheduler.schedule_feed_fetch.schedule"), \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt) as mock_sleep:
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_sleep.assert_called_with(5)

    ### Debug logging branch (line 28)

    def test_debug_logged_in_loop_when_level_is_debug(self):
        import logging
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles"), \
             patch("scheduler.schedule_feed_fetch.schedule"), \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt), \
             patch("scheduler.schedule_feed_fetch.logger") as mock_logger:
            mock_logger.level = logging.DEBUG
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_logger.debug.assert_called()

    def test_debug_not_logged_when_level_is_info(self):
        import logging
        with patch("scheduler.schedule_feed_fetch.fetch_all_articles"), \
             patch("scheduler.schedule_feed_fetch.schedule"), \
             patch("scheduler.schedule_feed_fetch.time.sleep", side_effect=KeyboardInterrupt), \
             patch("scheduler.schedule_feed_fetch.logger") as mock_logger:
            mock_logger.level = logging.INFO
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_logger.debug.assert_not_called()