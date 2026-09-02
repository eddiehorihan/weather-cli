"""Stable weather report shapes used by ASCII output and --json."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Location:
    query: str
    city: str
    state: str
    display_name: str
    latitude: float
    longitude: float
    timezone: str | None = None


@dataclass(frozen=True)
class CurrentConditions:
    condition: str | None
    temperature_f: float | None
    temperature_c: float | None
    wind_mph: float | None
    wind_direction_degrees: int | None
    humidity_percent: int | None
    station_id: str | None
    station_name: str | None
    observed_at: str | None


@dataclass(frozen=True)
class ForecastPeriod:
    name: str
    is_daytime: bool
    temperature_f: int | None
    temperature_unit: str
    wind: str
    short_forecast: str
    detailed_forecast: str


@dataclass(frozen=True)
class WeatherReport:
    location: Location
    current: CurrentConditions
    forecast: list[ForecastPeriod]

    def to_json_dict(self) -> dict:
        return {
            "ok": True,
            "source": "nws",
            "location": asdict(self.location),
            "current": asdict(self.current),
            "forecast": [asdict(period) for period in self.forecast],
        }
