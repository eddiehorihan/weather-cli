"""Smoke tests for place parsing, JSON shape, and a mocked NWS fetch."""

from __future__ import annotations

import io
import json
import re
import unittest
from urllib.parse import parse_qs, urlparse

from hashlib import sha256
from weather_cli.banner import (
    BANNER_LINES,
    BANNER_SHA256,
    BANNER_WIDTH,
    COMPACT_TITLE,
    banner_mode,
    render_banner,
)
from weather_cli.cli import run
from weather_cli.client import FORECAST_PERIODS, fetch_report
from weather_cli.display import (
    BLOCK_DIGITS,
    block_number,
    compass,
    group_forecast,
    group_hi_lo,
    icon_kind,
    layout_tier,
    mini_glyph,
    render_ascii,
    render_json,
    temp_axis,
    temp_bar,
    weather_icon,
)
from weather_cli.glyphs import MINI
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

LONG_DETAIL = (
    "A chance of showers and thunderstorms. Partly sunny, with a high near 77. "
    "Heat index values as high as 82. Southeast wind 5 to 10 mph. Chance of "
    "precipitation is 40 percent. New rainfall amounts between a tenth and "
    "quarter of an inch possible. Some storms may produce small hail and gusty "
    "winds this afternoon into early evening across the metro and nearby lakes."
)

_ANSI = re.compile(r"\033\[[0-9;]*m")
_ALLOWED_ANSI = {"0", "1", "2", "90", "97"}


def _visible(text: str) -> str:
    return _ANSI.sub("", text)


def _squeezed(text: str) -> str:
    parts: list[str] = []
    for row in text.splitlines():
        plain = _visible(row).strip()
        if plain.startswith("│") and plain.endswith("│"):
            plain = plain[1:-1].strip()
        elif plain.startswith(("╭", "╰")):
            continue
        if plain:
            parts.append(plain)
    return " ".join(" ".join(parts).split())


def _card_rows(art: str) -> list[str]:
    rows = []
    for row in art.splitlines():
        plain = _visible(row)
        if plain[:1] in {"╭", "│", "╰"}:
            rows.append(plain)
    return rows


def _column_texts(art: str) -> tuple[str, str]:
    """Split card rows on an interior day│night gutter; other rows stay left."""
    left_parts: list[str] = []
    right_parts: list[str] = []
    for row in art.splitlines():
        plain = _visible(row)
        if plain.startswith(("╭", "╰")):
            continue
        if plain.startswith("│") and plain.endswith("│"):
            inner = plain[1:-1]
            if " │ " in inner:
                left, right = inner.split(" │ ", 1)
                left_parts.append(left.strip())
                right_parts.append(right.strip())
            else:
                left_parts.append(inner.strip())
        elif plain.strip():
            left_parts.append(plain.strip())
    left = " ".join(" ".join(left_parts).split())
    right = " ".join(" ".join(right_parts).split())
    return left, right


def _sample_report(**overrides: object) -> WeatherReport:
    report = WeatherReport(
        location=Location("X", "Maple Grove", "MN", "Maple Grove, MN", 45.1, -93.4, "America/Chicago"),
        current=CurrentConditions(
            "Clear", 84.2, 29.0, 8.1, 135, 62, "KMIC", "Minneapolis, Crystal Airport",
            "2026-09-02T20:10:00+00:00",
        ),
        forecast=[],
    )
    if overrides:
        report = WeatherReport(
            location=overrides.get("location", report.location),  # type: ignore[arg-type]
            current=overrides.get("current", report.current),  # type: ignore[arg-type]
            forecast=overrides.get("forecast", report.forecast),  # type: ignore[arg-type]
        )
    return report


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
                detail=LONG_DETAIL,
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
        self.assertGreaterEqual(len(LONG_DETAIL), 300)
        self.assertIn(LONG_DETAIL, _squeezed(art))
        self.assertIn("high", art)
        self.assertIn("low", art)
        self.assertIn("83°", art)
        self.assertIn("68° / 83°", art)
        self.assertTrue("-o-" in art or "(`." in art)
        self.assertIn("low ━━━ high", art)
        self.assertNotIn("short forecast", art.lower())

    def test_ascii_grey_white_not_rainbow(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=True, width=76)
        self.assertNotIn("\033[36m", art)
        self.assertNotIn("\033[33m", art)
        self.assertNotIn("\033[34m", art)
        self.assertIn("\033[90m", art)
        self.assertIn("\033[97m", art)
        codes = set(re.findall(r"\033\[([0-9;]*)m", art))
        self.assertTrue(codes <= _ALLOWED_ANSI)

    def test_ascii_narrow_width_keeps_box(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=50, banner=False)
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
            ("Windy", True),
            ("Partly Cloudy", False),
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

    def test_full_detailed_forecast_no_ellipsis(self) -> None:
        self.assertGreaterEqual(len(LONG_DETAIL), 300)
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        for width in (48, 60, 76, 100, 140, 200):
            art = render_ascii(report, color=False, width=width, banner=False)
            self.assertNotIn("…", art, width)
            if layout_tier(width) == "l":
                left, _right = _column_texts(art)
                self.assertIn(LONG_DETAIL, left, width)
            else:
                self.assertIn(LONG_DETAIL, _squeezed(art), width)
            rows = _card_rows(art)
            self.assertTrue(rows)
            self.assertEqual({len(row) for row in rows}, {width + 4}, width)

    def test_width_not_clamped(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=160, banner=False)
        rows = _card_rows(art)
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 164 for row in rows))


class BannerTests(unittest.TestCase):
    def test_banner_sha256(self) -> None:
        blob = "\n".join(BANNER_LINES)
        self.assertEqual(sha256(blob.encode()).hexdigest(), BANNER_SHA256)
        self.assertEqual(
            BANNER_SHA256,
            "ca68821387f71bce0b82c9ed221a87e498e488ca777eefd097422a9a5bf7f9f6",
        )
        self.assertEqual([len(line) for line in BANNER_LINES], [177] * 9 + [176])

    def test_banner_mode_boundaries(self) -> None:
        self.assertEqual(banner_mode(BANNER_WIDTH), "full")
        self.assertEqual(banner_mode(177), "full")
        self.assertEqual(banner_mode(176), "stacked")
        self.assertEqual(banner_mode(127), "stacked")
        self.assertEqual(banner_mode(126), "compact")
        self.assertEqual(banner_mode(80), "compact")

    def test_full_stacked_compact_render(self) -> None:
        full = render_banner(177)
        self.assertEqual(len(full), 10)
        self.assertEqual(full[0], BANNER_LINES[0].ljust(177))
        self.assertEqual(full[-1], BANNER_LINES[-1].ljust(177))

        stacked = render_banner(150)
        self.assertEqual(len(stacked), 20)
        padded = BANNER_LINES[0].ljust(177)
        self.assertIn(padded[0:125].rstrip(), stacked[0])
        self.assertIn(padded[136:177].strip(), stacked[10])

        compact = render_banner(80, card_width=76)
        self.assertEqual(len(compact), 2)
        self.assertIn(COMPACT_TITLE, compact[0])
        self.assertEqual(len(compact[1]), 76)


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
        self.assertEqual(set(payload), {"ok", "source", "location", "current", "forecast"})
        self.assertEqual(len(payload["forecast"]), 14)
        self.assertNotIn("W E A T H E R", stdout.getvalue())
        self.assertNotIn("888888888o", stdout.getvalue())

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

    def test_no_banner_and_width_flags(self) -> None:
        stdout = io.StringIO()
        code = run(
            ["--no-banner", "--no-color", "--width", "64", "Minneapolis, MN"],
            stdin=io.StringIO(""),
            stdout=stdout,
            stderr=io.StringIO(),
            fetch=fake_fetch,
        )
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertNotIn("W E A T H E R", text)
        self.assertNotIn("888888888o", text)
        rows = _card_rows(text)
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 64 for row in rows))

    def test_width_below_minimum_rejected(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run(
            ["--width", "40", "Minneapolis, MN"],
            stdin=io.StringIO(""),
            stdout=stdout,
            stderr=stderr,
            fetch=fake_fetch,
        )
        self.assertEqual(code, 2)

    def test_compass(self) -> None:
        self.assertEqual(compass(0), "N")
        self.assertEqual(compass(225), "SW")


class LayoutTests(unittest.TestCase):
    def test_layout_tiers(self) -> None:
        self.assertEqual(layout_tier(48), "xs")
        self.assertEqual(layout_tier(63), "xs")
        self.assertEqual(layout_tier(64), "s")
        self.assertEqual(layout_tier(95), "s")
        self.assertEqual(layout_tier(96), "m")
        self.assertEqual(layout_tier(127), "m")
        self.assertEqual(layout_tier(128), "l")
        self.assertEqual(layout_tier(200), "l")

    def test_block_digits(self) -> None:
        allowed = set("█▀▄ ")
        for key, rows in BLOCK_DIGITS.items():
            self.assertEqual(len(rows), 3, key)
            self.assertTrue(all(len(row) == 3 for row in rows), key)
            self.assertTrue(all(set(row) <= allowed for row in rows), key)
        for value in (84, -12, 105):
            rows = block_number(value)
            self.assertEqual(len(rows), 3, value)
            self.assertEqual(len({len(row) for row in rows}), 1, value)
        report = _sample_report(
            current=CurrentConditions(None, None, None, None, None, None, None, None, None),
        )
        art = render_ascii(report, color=False, width=76, banner=False)
        self.assertIn("n/a", art)
        self.assertNotIn("█", art)
        self.assertNotIn("▀", art)
        self.assertNotIn("▄", art)

    def test_icon_kind_and_mini_glyph(self) -> None:
        cases = (
            ("Chance Showers And Thunderstorms", True, "thunder"),
            ("Mostly Clear", False, "moon"),
            ("Partly Cloudy", False, "partly-night"),
            ("Mostly Cloudy", True, "partly"),
            ("Windy", True, "wind"),
            ("Sunny", True, "sun"),
        )
        for text, daytime, kind in cases:
            self.assertEqual(icon_kind(text, daytime), kind, text)
            glyph = mini_glyph(text, daytime)
            self.assertEqual(len(glyph), 3, text)
            self.assertTrue(glyph.isascii(), text)
        for kind, glyph in MINI.items():
            self.assertEqual(len(glyph), 3, kind)
            self.assertTrue(glyph.isascii(), kind)

    def test_temp_axis_and_bar(self) -> None:
        wide = [
            ForecastPeriod("Today", True, 61, "F", "5 mph", "Sunny", "Sunny."),
            ForecastPeriod("Tonight", False, 73, "F", "5 mph", "Clear", "Clear."),
        ]
        self.assertEqual(temp_axis(wide), (60, 75))
        tight = [
            ForecastPeriod("Today", True, 70, "F", "5 mph", "Sunny", "Sunny."),
            ForecastPeriod("Tonight", False, 72, "F", "5 mph", "Clear", "Clear."),
        ]
        tmin, tmax = temp_axis(tight)
        self.assertEqual(tmin % 5, 0)
        self.assertEqual(tmax % 5, 0)
        self.assertGreaterEqual(tmax - tmin, 10)

        axis = (60, 80)
        bar = temp_bar(68, 78, axis, 20)
        self.assertEqual(len(bar), 20)
        self.assertIn("━", bar)
        self.assertTrue(set(bar) <= {"─", "━"})
        single = temp_bar(70, None, axis, 20)
        self.assertEqual(len(single), 20)
        self.assertEqual(single.count("●"), 1)
        self.assertTrue(set(single) <= {"─", "●"})
        empty = temp_bar(None, None, axis, 12)
        self.assertEqual(empty, "─" * 12)
        inverted = temp_bar(80, 60, axis, 11)
        normal = temp_bar(60, 80, axis, 11)
        self.assertEqual(inverted, normal)
        self.assertTrue(inverted.startswith("━") or "━" in inverted)

    def test_group_hi_lo(self) -> None:
        pair = [
            ForecastPeriod("Today", True, 80, "F", "5 mph", "Sunny", "Sunny."),
            ForecastPeriod("Tonight", False, 60, "F", "5 mph", "Clear", "Clear."),
        ]
        self.assertEqual(group_hi_lo(pair), (80, 60))
        lone = [ForecastPeriod("Tonight", False, 67, "F", "5 mph", "Clear", "Clear.")]
        self.assertEqual(group_hi_lo(lone), (None, 67))
        triple = [
            ForecastPeriod("Today", True, 80, "F", "5 mph", "Sunny", "Sunny."),
            ForecastPeriod("This Afternoon", True, 75, "F", "5 mph", "Cloudy", "Cloudy."),
            ForecastPeriod("Tonight", False, 60, "F", "5 mph", "Clear", "Clear."),
        ]
        self.assertEqual(group_hi_lo(triple), (80, 60))

    def test_strip_rows_align(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=76, banner=False)
        glyphs = r"(?:-o-|\(\.`|o_\)|`_\)|\(_\)|'''|\*\*\*|///|-_-|~~~)"
        pat = re.compile(rf"  {glyphs}  .{{4}} ([─━●]+) ")
        bars: list[tuple[int, int]] = []
        for row in _card_rows(art):
            if not row.startswith("│"):
                continue
            inner = row[2:-2]
            match = pat.search(inner)
            if match:
                bars.append((match.start(1), len(match.group(1))))
        self.assertGreaterEqual(len(bars), 2)
        self.assertEqual(len({span for span in bars}), 1)

    def test_two_column_ledger_wide(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=140, banner=False)
        same = [
            row
            for row in _card_rows(art)
            if "Chance Showers" in row and "Showers Likely" in row
        ]
        self.assertTrue(same)
        self.assertIn(" │ ", _visible(same[0]))
        in_tonight = False
        for row in _card_rows(art):
            if not row.startswith("│"):
                continue
            inner = row[2:-2]
            if inner.startswith("  Tonight ─"):
                in_tonight = True
            elif in_tonight and inner.startswith("  ") and not inner.startswith("    ") and "─" in inner:
                break
            if in_tonight:
                self.assertNotIn("│", inner, inner)

    def test_single_column_below_l(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        art = render_ascii(report, color=False, width=100, banner=False)
        for row in _card_rows(art):
            if row.startswith("│") and row.endswith("│"):
                self.assertNotIn("│", row[1:-1], row)

    def test_tiles_wrap_long_station(self) -> None:
        name = "West Lake Michigan Shoreline Observation Station Annex Bldg."
        self.assertEqual(len(name), 60)
        report = _sample_report(
            current=CurrentConditions(
                "Clear", 70, 21, 5, 180, 40, "KXXX", name, None
            ),
        )
        art = render_ascii(report, color=False, width=64, banner=False)
        self.assertNotIn("…", art)
        rows = _card_rows(art)
        self.assertEqual({len(row) for row in rows}, {68})
        self.assertIn(name, _squeezed(art))

    def test_summary_wind_never_splits(self) -> None:
        report = _sample_report(
            forecast=[
                ForecastPeriod(
                    "Today",
                    True,
                    89,
                    "F",
                    "5 to 10 mph SE",
                    "Slight Chance Showers And Thunderstorms",
                    "A slight chance of showers.",
                )
            ]
        )
        art = render_ascii(report, color=False, width=48, banner=False)
        self.assertIn("· 5 to 10 mph SE", _visible(art))
        self.assertNotIn("5 · to", _visible(art))
        found = False
        for row in _card_rows(art):
            if "· 5 to 10 mph SE" in row:
                found = True
        self.assertTrue(found)

    def test_dense_drops_spacers(self) -> None:
        report = fetch_report(parse_place("Minneapolis, MN"), fetch=fake_fetch)
        short = render_ascii(report, color=False, width=76, rows=20, banner=False)
        tall = render_ascii(report, color=False, width=76, rows=50, banner=False)
        self.assertLess(len(short.splitlines()), len(tall.splitlines()))
        rows = [row[2:-2] for row in _card_rows(short) if row.startswith("│")]
        forecast_at = next(
            index for index, row in enumerate(rows) if row.startswith("  Forecast")
        )
        following = rows[forecast_at + 1]
        self.assertTrue(following.strip(), "blank card row after Forecast in dense mode")

    def test_holiday_label_hard_cut_no_ellipsis(self) -> None:
        report = _sample_report(
            forecast=[
                ForecastPeriod(
                    "Washington's Birthday",
                    True,
                    45,
                    "F",
                    "10 mph NW",
                    "Sunny",
                    "Sunny, with a high near 45.",
                )
            ]
        )
        art = render_ascii(report, color=False, width=48, banner=False)
        self.assertNotIn("…", art)
        rows = _card_rows(art)
        self.assertEqual({len(row) for row in rows}, {52})
        self.assertIn("Washington's Birthday", art)


if __name__ == "__main__":
    unittest.main()
