import itertools

from a3m import common_metrics


def test_db_retry_timer_ignores_wall_clock_steps(mocker):
    mocker.patch("time.time", side_effect=itertools.count(100.0, -2.0))

    with common_metrics.db_retry_timer(description="test"):
        pass
