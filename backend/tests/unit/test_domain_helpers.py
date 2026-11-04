from datetime import datetime, timedelta, timezone

import pytest

from app.domain.freshness import FreshnessPolicy
from app.domain.normalization import normalize_city

pytestmark = pytest.mark.unit

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Bangalore", "bangalore"),
        ("  Bengaluru ", "bengaluru"),
        ("SÃO   PAULO", "sao paulo"),
        ("New  York", "new york"),
        ("Zürich", "zurich"),
    ],
)
def test_normalize_city(raw, expected):
    assert normalize_city(raw) == expected


def test_reading_is_fresh_strictly_inside_the_window():
    policy = FreshnessPolicy(max_age=timedelta(minutes=5))

    assert policy.is_fresh(NOW - timedelta(minutes=4, seconds=59), NOW)
    assert not policy.is_fresh(NOW - timedelta(minutes=5), NOW)


def test_a_reading_from_the_future_is_never_fresh():
    assert not FreshnessPolicy().is_fresh(NOW + timedelta(seconds=1), NOW)
