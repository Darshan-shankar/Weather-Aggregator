from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class FreshnessPolicy:
    """A reading is 'fresh' (cache-servable) while younger than max_age."""

    max_age: timedelta = timedelta(minutes=5)

    def is_fresh(self, fetched_at: datetime, now: datetime) -> bool:
        age = now - fetched_at
        return timedelta(0) <= age < self.max_age
