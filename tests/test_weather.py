"""Smoke tests for place parsing, JSON shape, and a mocked NWS fetch."""

from __future__ import annotations

import io
import json
import unittest
from urllib.parse import parse_qs, urlparse

from weather_cli.cli import run
from weather_cli.client import fetch_report
from weather_cli.display import compass, render_ascii, render_json
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

FORECAST = {
    "properties": {
        "periods": [
            {
                "name": "Tonight",
                "isDaytime": False,
                "temperature": 67,
                "temperatureUnit": "F",
                "windSpeed": "5 mph",
                "windDirection": "NNE",
                "shortForecast": "Mostly Clear",
                "detailedForecast": "Mostly clear, with a low around 67.",
            },
            {
                "name": "Wednesday",
                "isDaytime": True,
                "temperature": 83,
                "temperatureUnit": "F",
                "windSpeed": "5 mph",
                "windDirection": "ENE",
                "shortForecast": "Mostly Sunny",
                "detailedForecast": "Mostly sunny, with a high near 83.",
            },
            {
                "name": "Wednesday Night",
                "isDaytime": False,
                "temperature": 68,
                "temperatureUnit": "F",
                "windSpeed": "5 mph",
                "windDirection": "ENE",
                "shortForecast": "Partly Cloudy",
                "detailedForecast": "Partly cloudy, with a low around 68.",
            },
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
        self.assertEqual(len(payload["forecast"]), 3)
        self.assertEqual(payload["forecast"][0]["name"], "Tonight")
        self.assertEqual(payload["forecast"][1]["short_forecast"], "Mostly Sunny")

    def test_ascii_includes_current_and_forecast(self) -> None:
        report = fetch_report(parse_place("Minneapolis MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False)
        self.assertIn("Minneapolis, MN", art)
        self.assertIn("71.6°F", art)
        self.assertIn("Clear", art)
        self.assertIn("Tonight", art)
        self.assertIn("Mostly Sunny", art)
        self.assertIn("weather-cli", art)

    def test_unknown_place(self) -> None:
        with self.assertRaises(RuntimeError):
            fetch_report(parse_place("Nowhereville, ZZ"), fetch=fake_fetch)


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
        self.assertIn("short forecast", text)

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
