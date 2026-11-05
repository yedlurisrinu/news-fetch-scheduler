"""
### Unit tests for src/scheduler/schedule_feed_fetch.py
Tests immediate execution, job registration, and polling loop behaviour.
The infinite while-loop is short-circuited by having time.sleep raise KeyboardInterrupt.
"""

from unittest.mock import patch

import pytest

from scheduler import schedule_feed_fetch
from scheduler.schedule_feed_fetch import schedule_fetch


@pytest.fixture(autouse=True)
def _heartbeat_in_tmp(tmp_path, monkeypatch):
    """Keep the loop's heartbeat file out of the real /tmp."""
    monkeypatch.setattr(schedule_feed_fetch, "HEARTBEAT_FILE", tmp_path / "heartbeat")


class TestScheduleFetch:
    ### Immediate execution

    def test_calls_fetch_all_articles_immediately(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles") as mock_fetch,
            patch("scheduler.schedule_feed_fetch.schedule"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        mock_fetch.assert_called()
        # First call must happen before the loop (immediate run)
        assert mock_fetch.call_count >= 1

    ### Job registration

    def test_registers_recurring_schedule(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        assert mock_schedule.every.call_count == 2  # fetch job + daily dedup refresh

    def test_schedule_interval_matches_settings(self):
        from config.news_scheduler_settings import get_setting

        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        mock_schedule.every.assert_any_call(get_setting("SCHEDULER_INTERVAL_MINUTES"))

    def test_do_registers_fetch_job_wrapper(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        # schedule.every(...).minutes.do(_run_fetch_job)
        do_call = mock_schedule.every.return_value.minutes.do
        do_call.assert_called_once_with(schedule_feed_fetch._run_fetch_job)

    def test_registers_daily_dedup_refresh_at_configured_time(self):
        from config.news_scheduler_settings import get_setting

        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        daily = mock_schedule.every.return_value.day
        daily.at.assert_called_once_with(get_setting("DEDUP_REFRESH_AT"))
        daily.at.return_value.do.assert_called_once_with(
            schedule_feed_fetch._run_dedup_refresh_job
        )

    def test_dedup_refresh_job_failure_is_logged_not_raised(self):
        with (
            patch(
                "scheduler.schedule_feed_fetch.refresh_dedup_cache",
                side_effect=RuntimeError("db down"),
            ),
            patch("scheduler.schedule_feed_fetch.logger") as logger,
        ):
            schedule_feed_fetch._run_dedup_refresh_job()  # must not raise
        logger.exception.assert_called_once()

    ### Job failures do not kill the scheduler

    def test_initial_fetch_failure_does_not_stop_scheduler(self):
        with (
            patch(
                "scheduler.schedule_feed_fetch.fetch_all_articles",
                side_effect=RuntimeError("db down"),
            ),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        mock_schedule.run_pending.assert_called()

    def test_run_fetch_job_logs_exception(self):
        with (
            patch(
                "scheduler.schedule_feed_fetch.fetch_all_articles",
                side_effect=RuntimeError("boom"),
            ),
            patch("scheduler.schedule_feed_fetch.logger") as mock_logger,
        ):
            schedule_feed_fetch._run_fetch_job()  # must not raise

        mock_logger.exception.assert_called_once()

    ### Heartbeat

    def test_heartbeat_file_touched_in_loop(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch("scheduler.schedule_feed_fetch.schedule"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        assert schedule_feed_fetch.HEARTBEAT_FILE.exists()

    ### Polling loop

    def test_run_pending_called_in_loop(self):
        call_count = {"n": 0}

        def sleep_side_effect(seconds):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise KeyboardInterrupt

        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=sleep_side_effect,
            ),
            patch("scheduler.schedule_feed_fetch.schedule") as mock_schedule,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        assert mock_schedule.run_pending.call_count >= 2

    def test_sleep_duration_is_5_seconds(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch("scheduler.schedule_feed_fetch.schedule"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ) as mock_sleep,
            pytest.raises(KeyboardInterrupt),
        ):
            schedule_fetch()

        mock_sleep.assert_called_with(5)

    ### Debug logging branch (line 28)

    def test_debug_logged_in_loop_when_level_is_debug(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch("scheduler.schedule_feed_fetch.schedule"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.logger") as mock_logger,
        ):
            mock_logger.isEnabledFor.return_value = True
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_logger.debug.assert_called()

    def test_debug_not_logged_when_level_is_info(self):
        with (
            patch("scheduler.schedule_feed_fetch.fetch_all_articles"),
            patch("scheduler.schedule_feed_fetch.schedule"),
            patch(
                "scheduler.schedule_feed_fetch.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("scheduler.schedule_feed_fetch.logger") as mock_logger,
        ):
            mock_logger.isEnabledFor.return_value = False
            with pytest.raises(KeyboardInterrupt):
                schedule_fetch()

        mock_logger.debug.assert_not_called()
