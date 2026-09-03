"""Human ASCII weather art and machine-readable JSON."""

from __future__ import annotations

import json
import math
import re
import shutil
import textwrap
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from weather_cli.banner import banner_mode, render_banner
from weather_cli.glyphs import (
    BLOCK_DIGITS,
    ICON_WIDTH,
    block_number,
    icon_kind,
    mini_glyph,
    weather_icon,
)
from weather_cli.models import CurrentConditions, ForecastPeriod, WeatherReport

MIN_WIDTH = 48
_ANSI = re.compile(r"\033\[[0-9;]*m")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREY = "\033[90m"
WHITE = "\033[97m"

CREDIT_LEFT = "NWS  ·  api.weather.gov"
CREDIT_RIGHT = "place: OpenStreetMap Nominatim"
CREDIT_FULL = f"{CREDIT_LEFT}  ·  {CREDIT_RIGHT}"

HERO_TEXT_COL = 17
TILE_COL = 40
HERO_TEXT_WIDE = TILE_COL - HERO_TEXT_COL - 2  # 21
PERIOD_PREFIX = 22
DETAIL_INDENT = 9
STRIP_LABEL_MIN = 9
STRIP_BAR_MIN = 8
STRIP_BAR_MAX = 40

__all__ = (
    "BLOCK_DIGITS",
    "ICON_WIDTH",
    "MIN_WIDTH",
    "block_number",
    "compass",
    "format_observed_at",
    "group_forecast",
    "group_hi_lo",
    "icon_kind",
    "layout_tier",
    "mini_glyph",
    "render_ascii",
    "render_json",
    "render_json_error",
    "resolve_size",
    "resolve_width",
    "temp_axis",
    "temp_bar",
    "weather_icon",
)


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


def _wrap_text(text: str, width: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if width < 8:
        return [_truncate(cleaned, max(width, 1))]
    return textwrap.wrap(
        cleaned,
        width=width,
        break_long_words=True,
        break_on_hyphens=True,
    )


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


def layout_tier(width: int) -> str:
    """Card layout tier from inner width."""
    if width < 64:
        return "xs"
    if width < 96:
        return "s"
    if width < 128:
        return "m"
    return "l"


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


def group_hi_lo(periods: list[ForecastPeriod]) -> tuple[int | None, int | None]:
    """Daytime max and night min for a forecast group."""
    day = [p.temperature_f for p in periods if p.is_daytime and p.temperature_f is not None]
    night = [
        p.temperature_f for p in periods if not p.is_daytime and p.temperature_f is not None
    ]
    hi = max(day) if day else None
    lo = min(night) if night else None
    return hi, lo


def temp_axis(periods: list[ForecastPeriod]) -> tuple[int, int]:
    """Shared strip axis, rounded outward to 5s and at least 10 wide."""
    temps = [p.temperature_f for p in periods if p.temperature_f is not None]
    if not temps:
        return 0, 10
    tmin = int(math.floor(min(temps) / 5) * 5)
    tmax = int(math.ceil(max(temps) / 5) * 5)
    if tmax - tmin < 10:
        tmax = tmin + 10
    return tmin, tmax


def temp_bar(
    lo: int | float | None,
    hi: int | float | None,
    axis: tuple[int, int],
    bar_width: int,
) -> str:
    """Plain `B`-cell range bar. Colouring is applied by the caller."""
    width = max(int(bar_width), 1)
    tmin, tmax = axis
    span = max(tmax - tmin, 1)

    def pos(value: int | float) -> int:
        return int(round((float(value) - tmin) / span * (width - 1)))

    if lo is None and hi is None:
        return "─" * width
    if lo is None or hi is None:
        cells = ["─"] * width
        cells[pos(hi if lo is None else lo)] = "●"
        return "".join(cells)
    start, end = sorted((pos(lo), pos(hi)))
    return "".join("━" if start <= index <= end else "─" for index in range(width))


def _columns(cells: list[list[str]], widths: list[int], gutter: str) -> list[str]:
    """Zip columns to a shared height and pad each cell to its width."""
    if not cells:
        return []
    height = max((len(col) for col in cells), default=0)
    rows: list[str] = []
    for index in range(height):
        parts: list[str] = []
        for col, width in zip(cells, widths):
            cell = col[index] if index < len(col) else ""
            parts.append(_pad(cell, width))
        rows.append(gutter.join(parts))
    return rows


def _header_lines(here: str, width: int, color: bool) -> list[str]:
    place = _paint(here, BOLD, WHITE, color=color)
    brand = _paint("weather-cli", GREY, color=color)
    if 2 + len(here) + 1 + len("weather-cli") <= width:
        return [_spread(f"  {place}", brand, width)]
    place_parts = _wrap_text(here, max(width - 2, 8)) or [here]
    lines = ["  " + _paint(part, BOLD, WHITE, color=color) for part in place_parts]
    lines.append(_spread("", brand, width))
    return lines


def _tile_items(current: CurrentConditions, loc_timezone: str | None) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    if current.wind_mph is not None or current.wind_direction_degrees is not None:
        items.append(("wind", _wind_label(current)))
    if current.humidity_percent is not None:
        items.append(("humidity", f"{current.humidity_percent}%"))
    observed = format_observed_at(current.observed_at, loc_timezone)
    if observed:
        items.append(("observed", observed))
    if current.station_id:
        station = current.station_id
        if current.station_name:
            station = f"{station} {current.station_name}"
        items.append(("station", " ".join(station.split())))
    if not items:
        items.append(("source", "National Weather Service"))
    return items


def _render_tile(label: str, value: str, width: int, color: bool) -> list[str]:
    wrap_width = max(width, 1)
    lines = [_paint(label, GREY, color=color)]
    parts = _wrap_text(value, wrap_width) or [""]
    lines.extend(_paint(part, WHITE, color=color) for part in parts)
    return lines


def _tile_grid(
    items: list[tuple[str, str]], avail_width: int, n_across: int, color: bool
) -> list[str]:
    if not items or n_across < 1 or avail_width < 1:
        return []
    base = max(avail_width // n_across, 1)
    rows: list[str] = []
    for start in range(0, len(items), n_across):
        chunk = items[start : start + n_across]
        widths = [base] * len(chunk)
        widths[-1] = max(avail_width - base * (len(chunk) - 1), 1)
        cells = [
            _render_tile(label, value, width, color)
            for (label, value), width in zip(chunk, widths)
        ]
        rows.extend(_columns(cells, widths, ""))
    return rows


def _tiles(
    current: CurrentConditions,
    loc_timezone: str | None,
    tier: str,
    width: int,
    color: bool,
) -> list[str]:
    items = _tile_items(current, loc_timezone)
    if tier in {"m", "l"}:
        return _tile_grid(items, max(width - TILE_COL, 1), 2, color)
    if tier == "s":
        grid = _tile_grid(items, max(width - 2, 1), 4, color)
    else:
        grid = _tile_grid(items, max(width - 2, 1), 2, color)
    return ["  " + row for row in grid]


def _hero_text_lines(
    current: CurrentConditions, text_width: int, color: bool
) -> list[str]:
    lines: list[str] = []
    if current.temperature_f is not None:
        digits = block_number(round(current.temperature_f))
        digits[0] = digits[0] + "°"
        widest = max(len(row) for row in digits)
        digits = [row.ljust(widest) for row in digits]
        lines.extend(_paint(row, BOLD, WHITE, color=color) for row in digits)
    else:
        lines.extend(["", _paint(_temp_label(None), BOLD, WHITE, color=color), ""])

    condition = (current.condition or "").strip()
    if condition:
        wrapped = _wrap_text(condition, max(text_width, 1)) or [condition]
        lines.extend(_paint(part, WHITE, color=color) for part in wrapped)
    else:
        lines.append("")

    if current.temperature_f is not None:
        exact = _temp_label(current.temperature_f)
        celsius = _temp_c_label(current.temperature_c)
        if celsius:
            exact = f"{exact}  ·  {celsius}"
        lines.append(_paint(exact, DIM, color=color))
    return lines


def _icon_text_rows(
    icon: list[str], text_lines: list[str], color: bool
) -> list[str]:
    painted_icon = [_paint(row, GREY, color=color) for row in icon]
    height = max(len(painted_icon), len(text_lines), 5)
    rows: list[str] = []
    blank_icon = " " * ICON_WIDTH
    for index in range(height):
        glyph = painted_icon[index] if index < len(painted_icon) else blank_icon
        extra = text_lines[index] if index < len(text_lines) else ""
        if extra:
            rows.append(f"  {glyph}   {extra}")
        else:
            rows.append(f"  {glyph}")
    return rows


def _hero_block(
    report: WeatherReport, width: int, tier: str, color: bool, *, dense: bool
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
    text_width = HERO_TEXT_WIDE if tier in {"m", "l"} else max(width - HERO_TEXT_COL, 1)
    text_lines = _hero_text_lines(current, text_width, color)
    icon_text = _icon_text_rows(icon, text_lines, color)
    tile_lines = _tiles(current, loc.timezone, tier, width, color)

    gap = [] if dense else [""]
    body: list[str] = [*gap, *header, *gap]
    if tier in {"m", "l"}:
        left = [_pad(row, TILE_COL) for row in icon_text]
        body.extend(_columns([left, tile_lines], [TILE_COL, max(width - TILE_COL, 1)], ""))
    else:
        body.extend(icon_text)
        body.extend(gap)
        body.extend(tile_lines)
    body.extend(gap)
    return body


def _paint_bar(bar: str, color: bool) -> str:
    parts: list[str] = []
    for cell in bar:
        if cell in {"━", "●"}:
            parts.append(_paint(cell, WHITE, color=color))
        else:
            parts.append(_paint(cell, GREY, color=color))
    return "".join(parts)


def _lohi_text(lo: int | None, hi: int | None) -> str:
    if lo is not None and hi is not None:
        return f"{lo}° / {hi}°"
    if lo is not None:
        return f"{lo}°"
    if hi is not None:
        return f"{hi}°"
    return ""


def _degree(value: int | None) -> str:
    if value is None:
        return ""
    return f"{value}°"


def _strip_block(
    groups: list[tuple[str, list[ForecastPeriod]]],
    width: int,
    color: bool,
    dense: bool,
) -> list[str]:
    del dense
    all_periods = [period for _, periods in groups for period in periods]
    if not any(period.temperature_f is not None for period in all_periods):
        return []

    labels = [label for label, _ in groups]
    label_width = max((len(label) for label in labels), default=STRIP_LABEL_MIN)
    label_width = min(max(label_width, STRIP_LABEL_MIN), max(width - 27, 1))
    bar_width = max(STRIP_BAR_MIN, min(STRIP_BAR_MAX, width - (label_width + 19)))
    axis = temp_axis(all_periods)

    rows: list[str] = []
    for label, periods in groups:
        shown = label[:label_width].ljust(label_width)
        daytime = next((period for period in periods if period.is_daytime), periods[0])
        glyph = mini_glyph(daytime.short_forecast, daytime.is_daytime)
        hi, lo = group_hi_lo(periods)
        bar = _paint_bar(temp_bar(lo, hi, axis, bar_width), color)
        lo_txt = _degree(lo).rjust(4)
        hi_txt = _degree(hi).ljust(4)
        rows.append(
            "  "
            + _paint(shown, WHITE, color=color)
            + "  "
            + _paint(glyph, GREY, color=color)
            + "  "
            + _paint(lo_txt, DIM, color=color)
            + " "
            + bar
            + " "
            + _paint(hi_txt, BOLD, WHITE, color=color)
        )
    return rows


def _day_header(
    title: str, lo: int | None, hi: int | None, width: int, color: bool
) -> str:
    lohi = _lohi_text(lo, hi)
    painted_title = _paint(title, BOLD, WHITE, color=color)
    if lohi:
        dashes = width - 4 - len(title) - len(lohi)
        rule = _paint("─" * max(dashes, 0), GREY, color=color)
        return f"  {painted_title} {rule} {_paint(lohi, GREY, color=color)}"
    dashes = width - 3 - len(title)
    rule = _paint("─" * max(dashes, 0), GREY, color=color)
    return f"  {painted_title} {rule}"


def _summary_parts(period: ForecastPeriod, summary_width: int) -> list[str]:
    short = period.short_forecast.strip()
    wind = period.wind.strip()
    if short and wind:
        combined = f"{short}  ·  {wind}"
        if len(combined) <= summary_width:
            return [combined]
        parts = _wrap_text(short, summary_width) or [short]
        wind_line = f"· {wind}"
        if len(wind_line) <= summary_width:
            parts.append(wind_line)
        else:
            wrapped_wind = _wrap_text(wind, max(summary_width - 2, 1)) or [wind]
            parts.append(f"· {wrapped_wind[0]}")
            parts.extend(wrapped_wind[1:])
        return parts
    if short:
        return _wrap_text(short, summary_width) or [short]
    if wind:
        return _wrap_text(wind, summary_width) or [wind]
    return [""]


def _period_lines(period: ForecastPeriod, col_width: int, color: bool) -> list[str]:
    kind = "high" if period.is_daytime else "low"
    if period.temperature_f is None:
        temp = "--"
    else:
        temp = f"{period.temperature_f}°"
    glyph = mini_glyph(period.short_forecast, period.is_daytime)
    prefix = (
        "    "
        + _paint(glyph, GREY, color=color)
        + "  "
        + _paint(f"{kind:<4}", GREY, color=color)
        + "  "
        + _paint(f"{temp:>4}", BOLD, WHITE, color=color)
        + "   "
    )
    summary_width = max(col_width - PERIOD_PREFIX, 1)
    summary_parts = _summary_parts(period, summary_width)
    lines = [prefix + _paint(summary_parts[0], WHITE, color=color)]
    hang = " " * PERIOD_PREFIX
    for extra in summary_parts[1:]:
        lines.append(hang + _paint(extra, WHITE, color=color))

    detail = period.detailed_forecast.strip()
    short = period.short_forecast.strip()
    if detail and detail.rstrip(".").lower() != short.rstrip(".").lower():
        detail_width = max(col_width - DETAIL_INDENT, 1)
        for wrapped in _wrap_text(detail, detail_width):
            lines.append(_paint((" " * DETAIL_INDENT) + wrapped, DIM, color=color))
    return lines


def _two_column_group(periods: list[ForecastPeriod]) -> bool:
    if len(periods) != 2:
        return False
    day = [period for period in periods if period.is_daytime]
    night = [period for period in periods if not period.is_daytime]
    return len(day) == 1 and len(night) == 1


def _ledger_group(
    heading: str,
    periods: list[ForecastPeriod],
    width: int,
    tier: str,
    color: bool,
) -> list[str]:
    hi, lo = group_hi_lo(periods)
    lines = [_day_header(heading, lo, hi, width, color)]
    if tier == "l" and _two_column_group(periods):
        day = next(period for period in periods if period.is_daytime)
        night = next(period for period in periods if not period.is_daytime)
        left_w = (width - 3) // 2
        right_w = width - left_w - 3
        gutter = " " + _paint("│", GREY, color=color) + " "
        lines.extend(
            _columns(
                [_period_lines(day, left_w, color), _period_lines(night, right_w, color)],
                [left_w, right_w],
                gutter,
            )
        )
    else:
        for period in periods:
            lines.extend(_period_lines(period, width, color))
    return lines


def _forecast_block(
    report: WeatherReport, width: int, tier: str, color: bool, *, dense: bool
) -> list[str]:
    legend = (
        _paint("low", GREY, color=color)
        + " "
        + _paint("━━━", WHITE, color=color)
        + " "
        + _paint("high", GREY, color=color)
    )
    title = _spread("  " + _paint("Forecast", BOLD, WHITE, color=color), legend, width)
    gap = [] if dense else [""]
    lines: list[str] = [title, *gap]
    if not report.forecast:
        lines.append("  " + _paint("No forecast periods returned.", DIM, color=color))
        lines.extend(gap)
        return lines

    groups = group_forecast(report.forecast)
    strip = _strip_block(groups, width, color, dense)
    if strip:
        lines.extend(strip)
        lines.extend(gap)

    for index, (label, periods) in enumerate(groups):
        if index:
            lines.extend(gap)
        heading = periods[0].name if len(periods) == 1 else label
        lines.extend(_ledger_group(heading, periods, width, tier, color))
    lines.extend(gap)
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
    tier = layout_tier(inner)
    dense = lines < 30
    rule = _paint("  " + "─" * max(inner - 2, 1), GREY, color=color)
    body = [
        *_hero_block(report, inner, tier, color, dense=dense),
        rule,
        *([] if dense else [""]),
        *_forecast_block(report, inner, tier, color, dense=dense),
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
