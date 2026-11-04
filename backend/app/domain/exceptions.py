"""Domain errors. Adapters translate infrastructure failures into these."""


class DomainError(Exception):
    """Base class for all domain-level errors."""


class CityNotFoundError(DomainError):
    def __init__(self, city: str) -> None:
        super().__init__(f"City not found: {city!r}")
        self.city = city


class WeatherProviderError(DomainError):
    """The external weather provider failed (timeout, 5xx, bad payload...)."""


class NoReadingsFoundError(DomainError):
    def __init__(self, city: str) -> None:
        super().__init__(f"No readings stored for city: {city!r}")
        self.city = city
