"""Human ASCII weather art and machine-readable JSON."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from weather_cli.models import CurrentConditions, WeatherReport

WIDTH = 58
_ANSI = re.compile(r"\033\[[0-9;]*m")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
WHITE = "\033[37m"


def _paint(text: str, *codes: str, color: bool) -> str:
    if not color or not codes:
        return text
    return "".join(codes) + text + RESET


def _visible_len(text: str) -> int:
    return len(_ANSI.sub("", text))


def _pad(text: str, width: int = WIDTH) -> str:
    vis = _visible_len(text)
    if vis >= width:
        return text
    return text + " " * (width - vis)


def _card(lines: list[str]) -> list[str]:
    top = "╭" + "─" * (WIDTH + 2) + "╮"
    bottom = "╰" + "─" * (WIDTH + 2) + "╯"
    body = [f"│ {_pad(line)} │" for line in lines]
    return [top, *body, bottom]


def compass(degrees: int | None) -> str:
    if degrees is None:
        return ""
    points = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )
    return points[int((degrees % 360) / 22.5 + 0.5) % 16]


def format_observed_at(observed_at: str | None, tz_name: str | None) -> str:
    if not observed_at:
        return ""
    try:
        stamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return observed_at
    if tz_name:
        try:
            stamp = stamp.astimezone(ZoneInfo(tz_name))
        except ZoneInfoNotFoundError:
            stamp = stamp.astimezone(timezone.utc)
    else:
        stamp = stamp.astimezone(timezone.utc)
    clock = stamp.strftime("%I:%M %p %Z").lstrip("0")
    return clock


def weather_icon(text: str, is_daytime: bool = True) -> list[str]:
    blob = text.lower()
    if any(word in blob for word in ("thunder", "t-storm", "tstm")):
        return [
            "      .--.      ",
            "   .-(    ).    ",
            "  (___.__)__)   ",
            "    / / /       ",
            "   / / /        ",
        ]
    if any(word in blob for word in ("snow", "flurries", "blizzard", "sleet", "ice")):
        return [
            "      .--.      ",
            "   .-(    ).    ",
            "  (___.__)__)   ",
            "    *  *  *     ",
            "   *  *  *      ",
        ]
    if any(word in blob for word in ("rain", "shower", "drizzle")):
        return [
            "      .--.      ",
            "   .-(    ).    ",
            "  (___.__)__)   ",
            "    ' ' ' '     ",
            "   ' ' ' '      ",
        ]
    if any(word in blob for word in ("fog", "haze", "mist", "smoke")):
        return [
            "                ",
            "   _ - _ - _    ",
            "    _ - _ -     ",
            "   _ - _ - _    ",
            "                ",
        ]
    if any(word in blob for word in ("overcast", "cloudy", "cloud")) and "partly" not in blob:
        return [
            "                ",
            "      .--.      ",
            "   .-(    ).    ",
            "  (___.__)__)   ",
            "                ",
        ]
    if not is_daytime and any(word in blob for word in ("clear", "fair", "sunny")):
        return [
            "                ",
            "      .-.       ",
            "     (  '       ",
            "      `-'       ",
            "                ",
        ]
    # Default: sun, including partly cloudy / mostly sunny.
    return [
        "     \\   /      ",
        "      .-.       ",
        "   ― (   ) ―    ",
        "      `-'       ",
        "     /   \\      ",
    ]


def _temp_label(temp_f: float | None) -> str:
    if temp_f is None:
        return "n/a"
    if float(temp_f).is_integer():
        return f"{int(temp_f)}°F"
    return f"{temp_f:.1f}°F"


def _wind_label(current: CurrentConditions) -> str:
    if current.wind_mph is None:
        return "wind n/a"
    if current.wind_mph < 1:
        return "wind calm"
    direction = compass(current.wind_direction_degrees)
    if direction:
        return f"wind {current.wind_mph:g} mph {direction}"
    return f"wind {current.wind_mph:g} mph"


def render_ascii(report: WeatherReport, color: bool = True) -> str:
    loc = report.location
    here = f"{loc.city}, {loc.state}".strip(", ")
    current = report.current
    icon_source = current.condition or (
        report.forecast[0].short_forecast if report.forecast else ""
    )
    is_day = True
    if report.forecast:
        is_day = report.forecast[0].is_daytime
    icon = weather_icon(icon_source, is_daytime=is_day)

    title = _paint("weather-cli", BOLD, CYAN, color=color)
    place = _paint(here, BOLD, color=color)
    temp = _paint(_temp_label(current.temperature_f), BOLD, YELLOW, color=color)
    condition = current.condition or "Current conditions unavailable"
    bits = [_wind_label(current)]
    if current.humidity_percent is not None:
        bits.append(f"humidity {current.humidity_percent}%")
    meta = " · ".join(bits)
    observed = format_observed_at(current.observed_at, loc.timezone)
    station = current.station_id or ""
    foot_parts = [part for part in (station, observed) if part]
    footer = " · ".join(foot_parts) if foot_parts else "National Weather Service"

    now_lines = [
        "",
        f"  {icon[0]}{title}  ·  {place}",
        f"  {icon[1]}{_paint('National Weather Service · USA', DIM, color=color)}",
        f"  {icon[2]}{temp}  {condition}",
        f"  {icon[3]}{meta}",
        f"  {icon[4]}{_paint(footer, DIM, color=color)}",
        "",
    ]

    forecast_lines = ["  " + _paint("short forecast", BOLD, color=color), ""]
    if not report.forecast:
        forecast_lines.append("  No forecast periods returned.")
    for period in report.forecast:
        name = period.name[:16]
        temp_f = f"{period.temperature_f}°" if period.temperature_f is not None else "--"
        summary = period.short_forecast
        row = f"  {name:<16}  {temp_f:>4}   {summary}"
        if len(row) > WIDTH:
            row = row[: WIDTH - 1] + "…"
        tint = YELLOW if period.is_daytime else BLUE
        forecast_lines.append(_paint(row, tint, color=color) if color else row)

    forecast_lines.append("")
    forecast_lines.append(
        _paint("  data: api.weather.gov  ·  place: OpenStreetMap Nominatim", DIM, color=color)
    )

    blocks = [
        *_card(now_lines),
        "",
        *_card(forecast_lines),
    ]
    return "\n".join(blocks)


def render_json(report: WeatherReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, ensure_ascii=True)


def render_json_error(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, indent=2, ensure_ascii=True)
