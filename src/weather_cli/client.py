"""Geocode a US city and fetch current + forecast data from NWS."""

from __future__ import annotations

from urllib.parse import urlencode

from weather_cli.http import JsonFetcher, fetch_json
from weather_cli.models import (
    CurrentConditions,
    ForecastPeriod,
    Location,
    WeatherReport,
)
from weather_cli.place import Place

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
FORECAST_PERIODS = 14
STATION_TRIES = 3


def c_to_f(celsius: float) -> float:
    return round(celsius * 9.0 / 5.0 + 32.0, 1)


def kmh_to_mph(kmh: float) -> float:
    return round(kmh * 0.621371, 1)


def _quantity_value(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("value")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def geocode_us_place(place: Place, fetch: JsonFetcher = fetch_json) -> Location:
    params = {
        "format": "json",
        "limit": "1",
        "addressdetails": "1",
        "countrycodes": "us",
        "q": f"{place.query_string()}, USA",
    }
    url = f"{NOMINATIM_URL}?{urlencode(params)}"
    results = fetch(url)
    if not isinstance(results, list) or not results:
        raise RuntimeError(
            f"Couldn't find {place.query_string()!r} in the USA. "
            "Try City, ST — like Minneapolis, MN."
        )
    hit = results[0]
    address = hit.get("address") or {}
    country = str(address.get("country_code") or "us").lower()
    if country not in {"us", "usa"}:
        raise RuntimeError(
            f"{place.query_string()!r} is outside the USA. "
            "v1 only covers the United States via the National Weather Service."
        )
    try:
        latitude = float(hit["lat"])
        longitude = float(hit["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Geocoder returned a place without coordinates.") from exc

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or place.city
    )
    state = address.get("state") or place.state or ""
    display = hit.get("display_name") or place.query_string()
    return Location(
        query=place.query_string(),
        city=str(city),
        state=str(state),
        display_name=str(display),
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
    )


def _current_from_observation(
    payload: dict, station_id: str, station_name: str
) -> CurrentConditions:
    props = payload.get("properties") or {}
    temp_c = _quantity_value(props.get("temperature"))
    wind_kmh = _quantity_value(props.get("windSpeed"))
    wind_dir = _quantity_value(props.get("windDirection"))
    humidity = _quantity_value(props.get("relativeHumidity"))
    condition = props.get("textDescription")
    return CurrentConditions(
        condition=str(condition) if condition else None,
        temperature_f=c_to_f(temp_c) if temp_c is not None else None,
        temperature_c=round(temp_c, 1) if temp_c is not None else None,
        wind_mph=kmh_to_mph(wind_kmh) if wind_kmh is not None else None,
        wind_direction_degrees=int(round(wind_dir)) if wind_dir is not None else None,
        humidity_percent=int(round(humidity)) if humidity is not None else None,
        station_id=station_id,
        station_name=station_name or None,
        observed_at=props.get("timestamp"),
    )


def _usable_current(current: CurrentConditions) -> bool:
    return current.temperature_f is not None or bool(current.condition)


def fetch_report(place: Place, fetch: JsonFetcher = fetch_json) -> WeatherReport:
    location = geocode_us_place(place, fetch=fetch)
    points = fetch(
        NWS_POINTS_URL.format(lat=location.latitude, lon=location.longitude)
    )
    props = points.get("properties") or {}
    relative = (props.get("relativeLocation") or {}).get("properties") or {}
    city = relative.get("city") or location.city
    state = relative.get("state") or location.state
    timezone = props.get("timeZone")
    location = Location(
        query=location.query,
        city=str(city),
        state=str(state),
        display_name=location.display_name,
        latitude=location.latitude,
        longitude=location.longitude,
        timezone=str(timezone) if timezone else None,
    )

    forecast_url = props.get("forecast")
    stations_url = props.get("observationStations")
    if not forecast_url:
        raise RuntimeError(
            "National Weather Service did not return a forecast for that point."
        )

    forecast_payload = fetch(forecast_url)
    raw_periods = (forecast_payload.get("properties") or {}).get("periods") or []
    forecast: list[ForecastPeriod] = []
    for raw in raw_periods[:FORECAST_PERIODS]:
        temp = raw.get("temperature")
        wind_speed = raw.get("windSpeed") or ""
        wind_dir = raw.get("windDirection") or ""
        wind = " ".join(part for part in (str(wind_speed), str(wind_dir)) if part).strip()
        forecast.append(
            ForecastPeriod(
                name=str(raw.get("name") or "Period"),
                is_daytime=bool(raw.get("isDaytime")),
                temperature_f=int(temp) if isinstance(temp, (int, float)) else None,
                temperature_unit=str(raw.get("temperatureUnit") or "F"),
                wind=wind,
                short_forecast=str(raw.get("shortForecast") or ""),
                detailed_forecast=str(raw.get("detailedForecast") or ""),
            )
        )

    current = CurrentConditions(
        condition=None,
        temperature_f=None,
        temperature_c=None,
        wind_mph=None,
        wind_direction_degrees=None,
        humidity_percent=None,
        station_id=None,
        station_name=None,
        observed_at=None,
    )
    backup: CurrentConditions | None = None
    if stations_url:
        stations_payload = fetch(stations_url)
        features = stations_payload.get("features") or []
        for feature in features[:STATION_TRIES]:
            station_props = feature.get("properties") or {}
            station_id = station_props.get("stationIdentifier")
            if not station_id:
                continue
            station_name = str(station_props.get("name") or station_id)
            try:
                obs = fetch(
                    f"https://api.weather.gov/stations/{station_id}/observations/latest"
                )
            except RuntimeError:
                continue
            candidate = _current_from_observation(obs, str(station_id), station_name)
            if not _usable_current(candidate):
                continue
            if candidate.condition:
                current = candidate
                break
            if backup is None:
                backup = candidate
        if not _usable_current(current) and backup is not None:
            current = backup

    if not forecast and not _usable_current(current):
        raise RuntimeError("National Weather Service returned no current or forecast data.")

    return WeatherReport(location=location, current=current, forecast=forecast)
