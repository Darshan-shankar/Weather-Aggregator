from datetime import datetime, timezone

from app.ports.outbound import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
