"""Smoke tests for place parsing, JSON shape, and a mocked NWS fetch."""

from __future__ import annotations

import io
import json
import unittest
from urllib.parse import parse_qs, urlparse

from weather_cli.cli import run
from weather_cli.client import FORECAST_PERIODS, fetch_report
from weather_cli.display import (
    compass,
    group_forecast,
    render_ascii,
    render_json,
    weather_icon,
)
from weather_cli.models import CurrentConditions, ForecastPeriod, Location, WeatherReport
from weather_cli.place import parse_place


NOMINATIM = [
    {
        "lat": "44.9773",
        "lon": "-93.2655",
        "display_name": "Minneapolis, Hennepin County, Minnesota, United States",
        "address": {
            "city": "Minneapolis",
            "state": "Minnesota",
            "country_code": "us",
        },
    }
]

POINTS = {
    "properties": {
        "forecast": "https://api.weather.gov/gridpoints/MPX/108,72/forecast",
        "observationStations": "https://api.weather.gov/gridpoints/MPX/108,72/stations",
        "timeZone": "America/Chicago",
        "relativeLocation": {
            "properties": {"city": "Minneapolis", "state": "MN"}
        },
    }
}

def _nws_period(
    name: str,
    *,
    daytime: bool,
    temp: int,
    short: str,
    detail: str,
    wind_speed: str = "5 mph",
    wind_dir: str = "ENE",
) -> dict:
    return {
        "name": name,
        "isDaytime": daytime,
        "temperature": temp,
        "temperatureUnit": "F",
        "windSpeed": wind_speed,
        "windDirection": wind_dir,
        "shortForecast": short,
        "detailedForecast": detail,
    }


FORECAST = {
    "properties": {
        "periods": [
            _nws_period(
                "Tonight",
                daytime=False,
                temp=67,
                short="Mostly Clear",
                detail="Mostly clear, with a low around 67.",
                wind_dir="NNE",
            ),
            _nws_period(
                "Wednesday",
                daytime=True,
                temp=83,
                short="Mostly Sunny",
                detail="Mostly sunny, with a high near 83.",
            ),
            _nws_period(
                "Wednesday Night",
                daytime=False,
                temp=68,
                short="Partly Cloudy",
                detail="Partly cloudy, with a low around 68.",
            ),
            _nws_period(
                "Thursday",
                daytime=True,
                temp=81,
                short="Mostly Sunny",
                detail="Mostly sunny, with a high near 81. A slight chance of showers after 3pm.",
            ),
            _nws_period(
                "Thursday Night",
                daytime=False,
                temp=66,
                short="Mostly Clear",
                detail="Mostly clear, with a low around 66.",
            ),
            _nws_period(
                "Friday",
                daytime=True,
                temp=79,
                short="Partly Sunny",
                detail="Partly sunny, with a high near 79.",
            ),
            _nws_period(
                "Friday Night",
                daytime=False,
                temp=64,
                short="Mostly Cloudy",
                detail="Mostly cloudy, with a low around 64.",
            ),
            _nws_period(
                "Saturday",
                daytime=True,
                temp=77,
                short="Chance Showers",
                detail=(
                    "A chance of showers. Partly sunny, with a high near 77. "
                    "Chance of precipitation is 40%."
                ),
            ),
            _nws_period(
                "Saturday Night",
                daytime=False,
                temp=62,
                short="Showers Likely",
                detail="Showers likely, with a low around 62.",
            ),
            _nws_period(
                "Sunday",
                daytime=True,
                temp=74,
                short="Partly Sunny",
                detail="Partly sunny, with a high near 74.",
            ),
            _nws_period(
                "Sunday Night",
                daytime=False,
                temp=60,
                short="Mostly Clear",
                detail="Mostly clear, with a low around 60.",
            ),
            _nws_period(
                "Monday",
                daytime=True,
                temp=76,
                short="Sunny",
                detail="Sunny, with a high near 76.",
            ),
            _nws_period(
                "Monday Night",
                daytime=False,
                temp=61,
                short="Clear",
                detail="Clear, with a low around 61.",
            ),
            _nws_period(
                "Tuesday",
                daytime=True,
                temp=78,
                short="Mostly Sunny",
                detail="Mostly sunny, with a high near 78.",
            ),
            _nws_period(
                "Tuesday Night",
                daytime=False,
                temp=63,
                short="Partly Cloudy",
                detail="Partly cloudy, with a low around 63.",
            ),
        ]
    }
}

STATIONS = {
    "features": [
        {
            "properties": {
                "stationIdentifier": "KMSP",
                "name": "Minneapolis-St. Paul International Airport",
            }
        }
    ]
}

OBSERVATION = {
    "properties": {
        "textDescription": "Clear",
        "temperature": {"value": 22.0, "unitCode": "wmoUnit:degC"},
        "windSpeed": {"value": 8.0, "unitCode": "wmoUnit:km_h-1"},
        "windDirection": {"value": 225, "unitCode": "wmoUnit:degree_(angle)"},
        "relativeHumidity": {"value": 54.4, "unitCode": "wmoUnit:percent"},
        "timestamp": "2026-09-02T03:05:00+00:00",
    }
}


def fake_fetch(url: str):
    parsed = urlparse(url)
    if parsed.netloc == "nominatim.openstreetmap.org":
        query = parse_qs(parsed.query)
        q = (query.get("q") or [""])[0]
        if "Nowhereville" in q:
            return []
        return NOMINATIM
    if "/points/" in parsed.path:
        return POINTS
    if parsed.path.endswith("/forecast"):
        return FORECAST
    if parsed.path.endswith("/stations"):
        return STATIONS
    if parsed.path.endswith("/observations/latest"):
        return OBSERVATION
    raise AssertionError(f"unexpected URL: {url}")


class PlaceTests(unittest.TestCase):
    def test_comma_city_state(self) -> None:
        place = parse_place("Minneapolis, MN")
        self.assertEqual(place.city, "Minneapolis")
        self.assertEqual(place.state, "MN")

    def test_space_separated_and_full_name(self) -> None:
        place = parse_place("Austin Texas")
        self.assertEqual(place.city, "Austin")
        self.assertEqual(place.state, "TX")

    def test_empty_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_place("   ")

    def test_unknown_state_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_place("Atlantis, ZZ")


class ReportTests(unittest.TestCase):
    def test_mocked_nws_json_is_stable(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        payload = json.loads(render_json(report))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "nws")
        self.assertEqual(payload["location"]["city"], "Minneapolis")
        self.assertEqual(payload["location"]["state"], "MN")
        self.assertEqual(payload["location"]["latitude"], 44.9773)
        self.assertEqual(payload["current"]["condition"], "Clear")
        self.assertEqual(payload["current"]["temperature_c"], 22.0)
        self.assertEqual(payload["current"]["temperature_f"], 71.6)
        self.assertEqual(payload["current"]["station_id"], "KMSP")
        self.assertEqual(payload["current"]["humidity_percent"], 54)
        self.assertEqual(set(payload), {"ok", "source", "location", "current", "forecast"})
        self.assertEqual(FORECAST_PERIODS, 14)
        self.assertEqual(len(payload["forecast"]), 14)
        self.assertEqual(payload["forecast"][0]["name"], "Tonight")
        self.assertEqual(payload["forecast"][1]["short_forecast"], "Mostly Sunny")
        self.assertIn("detailed_forecast", payload["forecast"][0])
        self.assertEqual(payload["forecast"][7]["name"], "Saturday")

    def test_ascii_includes_current_and_forecast(self) -> None:
        report = fetch_report(parse_place("Minneapolis MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=76)
        self.assertIn("Minneapolis, MN", art)
        self.assertIn("71.6°F", art)
        self.assertIn("Clear", art)
        self.assertIn("Tonight", art)
        self.assertIn("Mostly Sunny", art)
        self.assertIn("weather-cli", art)
        self.assertIn("Forecast", art)
        self.assertIn("wind", art)
        self.assertIn("humidity", art)
        self.assertIn("KMSP", art)
        self.assertIn("Thursday", art)
        self.assertIn("Saturday", art)
        self.assertIn("Mostly clear, with a low around 67.", art)
        self.assertIn("A slight chance of showers after 3pm.", art)
        self.assertIn("high", art)
        self.assertIn("low", art)
        self.assertNotIn("short forecast", art.lower())

    def test_ascii_grey_white_not_rainbow(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=True, width=76)
        self.assertNotIn("\033[36m", art)
        self.assertNotIn("\033[33m", art)
        self.assertNotIn("\033[34m", art)
        self.assertIn("\033[90m", art)
        self.assertIn("\033[97m", art)

    def test_ascii_narrow_width_keeps_box(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=50)
        rows = [row for row in art.splitlines() if row]
        lengths = {len(row) for row in rows}
        self.assertEqual(len(lengths), 1)
        self.assertLessEqual(next(iter(lengths)), 56)

    def test_weather_icons_are_balanced(self) -> None:
        samples = (
            ("Thunderstorms", True),
            ("Snow", True),
            ("Rain Showers", True),
            ("Fog", True),
            ("Partly Cloudy", True),
            ("Overcast", True),
            ("Clear", False),
            ("Sunny", True),
        )
        for text, daytime in samples:
            icon = weather_icon(text, is_daytime=daytime)
            self.assertEqual(len(icon), 5, text)
            self.assertTrue(all(len(line) == 12 for line in icon), text)

    def test_group_forecast_pairs_day_and_night(self) -> None:
        periods = [
            ForecastPeriod("Today", True, 80, "F", "5 mph S", "Sunny", "Sunny."),
            ForecastPeriod("Tonight", False, 60, "F", "3 mph S", "Clear", "Clear."),
            ForecastPeriod("Wednesday", True, 83, "F", "5 mph E", "Sunny", "Sunny."),
            ForecastPeriod("Wednesday Night", False, 68, "F", "5 mph E", "Cloudy", "Cloudy."),
        ]
        groups = group_forecast(periods)
        self.assertEqual([label for label, _ in groups], ["Today", "Wednesday"])
        self.assertEqual(len(groups[0][1]), 2)
        self.assertEqual(len(groups[1][1]), 2)

        holiday = [
            ForecastPeriod("Labor Day", True, 79, "F", "5 mph E", "Sunny", "Sunny."),
            ForecastPeriod("Monday Night", False, 63, "F", "10 mph SE", "Cloudy", "Cloudy."),
        ]
        self.assertEqual([label for label, _ in group_forecast(holiday)], ["Labor Day", "Monday"])
        report = WeatherReport(
            location=Location("X", "Austin", "TX", "Austin, TX", 30.2, -97.7),
            current=CurrentConditions("Sunny", 80, 26.7, 5, 180, 40, "KAUS", None, None),
            forecast=holiday,
        )
        art = render_ascii(report, color=False, width=76)
        self.assertIn("Labor Day", art)
        self.assertIn("Monday Night", art)

    def test_unknown_place(self) -> None:
        with self.assertRaises(RuntimeError):
            fetch_report(parse_place("Nowhereville, MN"), fetch=fake_fetch)


class CliTests(unittest.TestCase):
    def test_json_flag(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run(
            ["--json", "Minneapolis, MN"],
            stdin=io.StringIO(""),
            stdout=stdout,
            stderr=stderr,
            fetch=fake_fetch,
        )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["current"]["condition"], "Clear")
        self.assertEqual(payload["forecast"][0]["temperature_f"], 67)

    def test_interactive_prompt(self) -> None:
        stdout = io.StringIO()
        stdin = io.StringIO("Minneapolis, MN\n")
        stdin.isatty = lambda: True  # type: ignore[method-assign]
        code = run(
            [],
            stdin=stdin,
            stdout=stdout,
            stderr=io.StringIO(),
            fetch=fake_fetch,
        )
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn("City and state", text)
        self.assertIn("Minneapolis, MN", text)
        self.assertIn("Forecast", text)

    def test_noninteractive_missing_place(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        stdin = io.StringIO("")
        stdin.isatty = lambda: False  # type: ignore[method-assign]
        code = run(
            [],
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            fetch=fake_fetch,
        )
        self.assertEqual(code, 1)
        self.assertIn("City and state required", stderr.getvalue())

    def test_compass(self) -> None:
        self.assertEqual(compass(0), "N")
        self.assertEqual(compass(225), "SW")


if __name__ == "__main__":
    unittest.main()
