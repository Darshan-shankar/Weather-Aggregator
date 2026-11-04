"""Application service. Depends only on ports and domain objects."""

from uuid import uuid4

from app.domain.exceptions import NoReadingsFoundError
from app.domain.freshness import FreshnessPolicy
from app.domain.models import FetchResult, Location, WeatherReading
from app.domain.normalization import normalize_city
from app.ports.inbound import WeatherUseCase
from app.ports.outbound import Clock, WeatherProviderPort, WeatherRepositoryPort


class WeatherService(WeatherUseCase):
    def __init__(
        self,
        provider: WeatherProviderPort,
        repository: WeatherRepositoryPort,
        clock: Clock,
        freshness: FreshnessPolicy | None = None,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._clock = clock
        self._freshness = freshness or FreshnessPolicy()

    def fetch_and_store(self, city: str, force_refresh: bool = False) -> FetchResult:
        key = normalize_city(city)
        location = self._repository.find_location_by_alias(key)

        if location is None:
            geo = self._provider.resolve_city(city)  # may raise CityNotFoundError
            location = self._repository.save_location(
                Location.from_geo(geo, id=uuid4()),
                aliases={key, normalize_city(geo.name)},
            )

        if not force_refresh:
            cached = self._fresh_latest(location)
            if cached is not None:
                return FetchResult(reading=cached, created=False)

        conditions = self._provider.get_current(location)  # may raise WeatherProviderError
        reading = WeatherReading.create(
            location, conditions, fetched_at=self._clock.now()
        )
        self._repository.save_reading(reading)
        return FetchResult(reading=reading, created=True)

    def get_readings(self, city: str) -> list[WeatherReading]:
        location = self._repository.find_location_by_alias(normalize_city(city))
        if location is None:
            return []
        return self._repository.find_readings(location.id)

    def get_latest(self, city: str) -> WeatherReading:
        location = self._repository.find_location_by_alias(normalize_city(city))
        latest = self._repository.find_latest(location.id) if location else None
        if latest is None:
            raise NoReadingsFoundError(city)
        return latest

    def _fresh_latest(self, location: Location) -> WeatherReading | None:
        latest = self._repository.find_latest(location.id)
        if latest and self._freshness.is_fresh(latest.fetched_at, self._clock.now()):
            return latest
        return None
