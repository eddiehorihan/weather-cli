"""Human ASCII weather art and machine-readable JSON."""

from __future__ import annotations

import json
import re
import shutil
import textwrap
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from weather_cli.banner import banner_mode, render_banner
from weather_cli.models import CurrentConditions, ForecastPeriod, WeatherReport

MIN_WIDTH = 48
ICON_WIDTH = 12
_ANSI = re.compile(r"\033\[[0-9;]*m")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREY = "\033[90m"
WHITE = "\033[97m"

CREDIT_LEFT = "NWS  ·  api.weather.gov"
CREDIT_RIGHT = "place: OpenStreetMap Nominatim"
CREDIT_FULL = f"{CREDIT_LEFT}  ·  {CREDIT_RIGHT}"


def _paint(text: str, *codes: str, color: bool) -> str:
    if not color or not codes:
        return text
    return "".join(codes) + text + RESET


def _visible_len(text: str) -> int:
    return len(_ANSI.sub("", text))


def _pad(text: str, width: int) -> str:
    vis = _visible_len(text)
    if vis == width:
        return text
    if vis < width:
        return text + " " * (width - vis)
    plain = _ANSI.sub("", text)
    if width <= 1:
        return "…"
    return plain[: width - 1] + "…"


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if _visible_len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def _wrap_text(text: str, width: int, max_lines: int | None = None) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if width < 8:
        return [_truncate(cleaned, max(width, 1))]
    wrapped = textwrap.wrap(
        cleaned,
        width=width,
        break_long_words=True,
        break_on_hyphens=True,
    )
    if max_lines is None or len(wrapped) <= max_lines:
        return wrapped
    last = wrapped[max_lines - 1]
    if len(last) >= width:
        last = last[: width - 1] + "…"
    else:
        last = last.rstrip(" .") + "…"
    return wrapped[: max_lines - 1] + [last]


def _hanging_lines(text: str, width: int, hang: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if width < 8:
        return [_truncate(cleaned, max(width, 1))]
    hang = max(int(hang), 0)
    wrapper = textwrap.TextWrapper(
        width=width,
        subsequent_indent=" " * hang,
        break_long_words=True,
        break_on_hyphens=True,
        drop_whitespace=True,
    )
    return wrapper.wrap(cleaned)


def _spread(left: str, right: str, width: int) -> str:
    space = width - _visible_len(left) - _visible_len(right)
    if space >= 1:
        return left + (" " * space) + right
    keep = width - _visible_len(right) - 1
    if keep < 4:
        return _truncate(f"{left} {right}".strip(), width)
    return _truncate(left, keep) + " " + right


def _card(lines: list[str], width: int, color: bool) -> list[str]:
    bar = _paint("│", GREY, color=color)
    top = _paint("╭" + "─" * (width + 2) + "╮", GREY, color=color)
    bottom = _paint("╰" + "─" * (width + 2) + "╯", GREY, color=color)
    body = [f"{bar} {_pad(line, width)} {bar}" for line in lines]
    return [top, *body, bottom]


def resolve_size(
    columns: int | None = None,
    rows: int | None = None,
) -> tuple[int, int]:
    """Terminal size. Honors COLUMNS/LINES via shutil.get_terminal_size."""
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        term_cols, term_rows = int(size.columns), int(size.lines)
    except OSError:
        term_cols, term_rows = 80, 24
    cols = int(columns) if columns is not None else term_cols
    lines = int(rows) if rows is not None else term_rows
    return max(1, cols), max(1, lines)


def resolve_width(width: int | None = None, columns: int | None = None) -> int:
    """Inner card width. Explicit values keep test semantics; auto fills the terminal."""
    if width is not None:
        return max(MIN_WIDTH, int(width))
    cols, _ = resolve_size(columns=columns)
    return max(MIN_WIDTH, cols - 5)


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


def _normalize_icon(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines[:5]:
        if len(line) < ICON_WIDTH:
            out.append(line + " " * (ICON_WIDTH - len(line)))
        else:
            out.append(line[:ICON_WIDTH])
    while len(out) < 5:
        out.append(" " * ICON_WIDTH)
    return out


def weather_icon(text: str, is_daytime: bool = True) -> list[str]:
    blob = text.lower()
    if any(word in blob for word in ("thunder", "t-storm", "tstm")):
        icon = [
            "    .--.    ",
            " .-(    ).  ",
            "(___.__)__) ",
            "   / / /    ",
            "    / /     ",
        ]
    elif any(word in blob for word in ("snow", "flurries", "blizzard", "sleet", "ice")):
        icon = [
            "    .--.    ",
            " .-(    ).  ",
            "(___.__)__) ",
            "   *  *  *  ",
            "  *  *  *   ",
        ]
    elif any(word in blob for word in ("rain", "shower", "drizzle")):
        icon = [
            "    .--.    ",
            " .-(    ).  ",
            "(___.__)__) ",
            "  '  '  '   ",
            " '  '  '    ",
        ]
    elif any(word in blob for word in ("fog", "haze", "mist", "smoke")):
        icon = [
            " _ - _ - _  ",
            "  _ - _ -   ",
            " _ - _ - _  ",
            "  _ - _ -   ",
            " _ - _ - _  ",
        ]
    elif any(word in blob for word in ("partly", "mostly sunny", "mostly clear")):
        icon = [
            "  \\  /      ",
            '_ /"".-.    ',
            "  \\_(   ).  ",
            "  /(___(__) ",
            "            ",
        ]
    elif any(word in blob for word in ("overcast", "cloudy", "cloud")):
        icon = [
            "            ",
            "    .--.    ",
            " .-(    ).  ",
            "(___.__)__) ",
            "            ",
        ]
    elif not is_daytime and any(word in blob for word in ("clear", "fair", "sunny")):
        icon = [
            "     .-.    ",
            "    (  `.   ",
            "    (   )   ",
            "     `-'    ",
            "            ",
        ]
    else:
        icon = [
            "   \\   /    ",
            "    .-.     ",
            " ― (   ) ―  ",
            "    `-'     ",
            "   /   \\    ",
        ]
    return _normalize_icon(icon)


def _temp_label(temp_f: float | None) -> str:
    if temp_f is None:
        return "n/a"
    if float(temp_f).is_integer():
        return f"{int(temp_f)}°F"
    return f"{temp_f:.1f}°F"


def _temp_c_label(temp_c: float | None) -> str:
    if temp_c is None:
        return ""
    if float(temp_c).is_integer():
        return f"{int(temp_c)}°C"
    return f"{temp_c:.1f}°C"


def _wind_label(current: CurrentConditions) -> str:
    if current.wind_mph is None:
        return "n/a"
    if current.wind_mph < 1:
        return "calm"
    direction = compass(current.wind_direction_degrees)
    if direction:
        return f"{current.wind_mph:g} mph {direction}"
    return f"{current.wind_mph:g} mph"


def _group_label(name: str) -> str:
    if name in {"Tonight", "Overnight"}:
        return name
    if name.endswith(" Night"):
        return name[: -len(" Night")].strip() or name
    if name in {"Today", "This Afternoon", "This Morning", "This Evening"}:
        return "Today"
    return name


def group_forecast(periods: list[ForecastPeriod]) -> list[tuple[str, list[ForecastPeriod]]]:
    """Cluster NWS day/night periods so a weekday reads as one block."""
    groups: list[tuple[str, list[ForecastPeriod]]] = []
    for period in periods:
        label = _group_label(period.name)
        if period.name in {"Tonight", "Overnight"} and groups and groups[-1][0] == "Today":
            groups[-1][1].append(period)
            continue
        if groups and groups[-1][0] == label:
            groups[-1][1].append(period)
        else:
            groups.append((label, [period]))
    return groups


def _meta_row(label: str, value: str, color: bool) -> str:
    return (
        "  "
        + _paint(f"{label:<10}", GREY, color=color)
        + "  "
        + _paint(value, WHITE, color=color)
    )


def _meta_wrapped(label: str, value: str, width: int, color: bool) -> list[str]:
    hang = 16
    parts = _hanging_lines(value, max(width - hang, 8), hang=0)
    if not parts:
        return [_meta_row(label, "", color)]
    lines = [_meta_row(label, parts[0], color)]
    for part in parts[1:]:
        lines.append((" " * hang) + _paint(part, WHITE, color=color))
    return lines


def _header_lines(here: str, width: int, color: bool) -> list[str]:
    place = _paint(here, BOLD, WHITE, color=color)
    brand = _paint("weather-cli", GREY, color=color)
    if 2 + len(here) + 1 + len("weather-cli") <= width:
        return [_spread(f"  {place}", brand, width)]
    place_parts = _wrap_text(here, max(width - 2, 8)) or [here]
    lines = ["  " + _paint(part, BOLD, WHITE, color=color) for part in place_parts]
    lines.append(_spread("", brand, width))
    return lines


def _current_block(
    report: WeatherReport, width: int, color: bool, *, dense: bool
) -> list[str]:
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

    header = _header_lines(here, width, color)

    temp = _paint(_temp_label(current.temperature_f), BOLD, WHITE, color=color)
    celsius = _temp_c_label(current.temperature_c)
    if celsius:
        temp = (
            f"{temp}  "
            + _paint("·", GREY, color=color)
            + "  "
            + _paint(celsius, DIM, color=color)
        )
    condition = _paint(current.condition or "", WHITE, color=color)

    while icon and not icon[-1].strip():
        icon.pop()

    text_by_row = {1: temp, 2: condition}
    icon_lines: list[str] = []
    for index, row in enumerate(icon):
        glyph = _paint(row, GREY, color=color)
        extra = text_by_row.get(index, "")
        if extra:
            icon_lines.append(f"  {glyph}  {extra}")
        else:
            icon_lines.append(f"  {glyph}")

    meta: list[str] = []
    if current.wind_mph is not None or current.wind_direction_degrees is not None:
        meta.append(_meta_row("wind", _wind_label(current), color))
    if current.humidity_percent is not None:
        meta.append(_meta_row("humidity", f"{current.humidity_percent}%", color))
    if current.station_id:
        station = current.station_id
        if current.station_name:
            station = f"{station}  {current.station_name}"
        meta.extend(_meta_wrapped("station", station, width, color))
    observed = format_observed_at(current.observed_at, loc.timezone)
    if observed:
        meta.append(_meta_row("observed", observed, color))
    if not meta:
        meta.append(_meta_row("source", "National Weather Service", color))

    gap = [] if dense else [""]
    return [
        *gap,
        *header,
        *gap,
        *icon_lines,
        *gap,
        *meta,
        *gap,
    ]


def _period_summary(period: ForecastPeriod) -> str:
    short = period.short_forecast.strip()
    wind = period.wind.strip()
    if short and wind:
        return f"{short}  ·  {wind}"
    return short or wind


def _period_lines(period: ForecastPeriod, width: int, color: bool) -> list[str]:
    kind = "high" if period.is_daytime else "low"
    if period.temperature_f is None:
        temp = "--"
    else:
        temp = f"{period.temperature_f}°"
    indent = "    "
    prefix_len = 17  # "    high    83°   "
    summary_width = max(width - prefix_len, 8)
    summary_parts = _hanging_lines(_period_summary(period), summary_width, hang=0)
    if not summary_parts:
        summary_parts = [""]
    head = (
        indent
        + _paint(f"{kind:<4}", GREY, color=color)
        + "  "
        + _paint(f"{temp:>4}", BOLD, WHITE, color=color)
        + "   "
        + _paint(summary_parts[0], WHITE, color=color)
    )
    lines = [head]
    hang = " " * prefix_len
    for extra in summary_parts[1:]:
        lines.append(_paint(f"{hang}{extra}", WHITE, color=color))
    detail = period.detailed_forecast.strip()
    short = period.short_forecast.strip()
    if detail and detail.rstrip(".").lower() != short.rstrip(".").lower():
        detail_width = max(width - 4, 8)
        for wrapped in _hanging_lines(detail, detail_width, hang=4):
            lines.append(_paint(f"{indent}{wrapped}", DIM, color=color))
    return lines


def _forecast_block(
    report: WeatherReport, width: int, color: bool, *, dense: bool
) -> list[str]:
    lines = [
        "  " + _paint("Forecast", BOLD, WHITE, color=color),
        *([] if dense else [""]),
    ]
    if not report.forecast:
        lines.append("  " + _paint("No forecast periods returned.", DIM, color=color))
        if not dense:
            lines.append("")
        return lines

    groups = group_forecast(report.forecast)
    for index, (label, periods) in enumerate(groups):
        if index and not dense:
            lines.append("")
        heading = periods[0].name if len(periods) == 1 else label
        lines.append("  " + _paint(heading, BOLD, WHITE, color=color))
        for period in periods:
            lines.extend(_period_lines(period, width, color))
    if not dense:
        lines.append("")
    return lines


def _credit_lines(width: int, color: bool) -> list[str]:
    text_width = max(width - 2, 1)
    if len(CREDIT_FULL) <= text_width:
        return [_paint("  " + CREDIT_FULL, GREY, color=color)]
    return [
        _paint("  " + CREDIT_LEFT, GREY, color=color),
        _paint("  " + CREDIT_RIGHT, GREY, color=color),
    ]


def render_ascii(
    report: WeatherReport,
    color: bool = True,
    width: int | None = None,
    rows: int | None = None,
    banner: bool = True,
) -> str:
    cols, lines = resolve_size(rows=rows)
    inner = resolve_width(width, columns=cols)
    dense = lines < 30
    rule = _paint("  " + "─" * max(inner - 2, 1), GREY, color=color)
    body = [
        *_current_block(report, inner, color, dense=dense),
        rule,
        *([] if dense else [""]),
        *_forecast_block(report, inner, color, dense=dense),
        *_credit_lines(inner, color),
        *([] if dense else [""]),
    ]
    card = _card(body, inner, color)
    if not banner:
        return "\n".join(card)
    total = inner + 4
    art = [_paint(line, GREY, color=color) for line in render_banner(cols, card_width=total)]
    if banner_mode(cols) != "compact":
        art.append("")
    return "\n".join([*art, *card])


def render_json(report: WeatherReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2, ensure_ascii=True)


def render_json_error(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, indent=2, ensure_ascii=True)
