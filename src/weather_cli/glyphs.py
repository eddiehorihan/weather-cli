"""ASCII weather icons, mini glyphs, and 3-row block digits."""

from __future__ import annotations

ICON_WIDTH = 12

ICONS: dict[str, tuple[str, ...]] = {
    "sun": (
        "     |      ",
        "    .-.     ",
        " - (   ) -  ",
        "    `-'     ",
        "     |      ",
    ),
    "moon": (
        " *   .-.    ",
        "    (  `.   ",
        " *  (   )   ",
        "     `-'    ",
        "            ",
    ),
    "partly": (
        "      .-.   ",
        "   - (   ) -",
        "    .--.    ",
        " .-(    ).  ",
        "(___.__)__) ",
    ),
    "partly-night": (
        "   .-.      ",
        "  (  `.-.   ",
        "   `--(   ).",
        "    (___(__)",
        "            ",
    ),
    "cloud": (
        "            ",
        "    .--.    ",
        " .-(    ).  ",
        "(___.__)__) ",
        "            ",
    ),
    "rain": (
        "    .--.    ",
        " .-(    ).  ",
        "(___.__)__) ",
        "   :  :  :  ",
        "  :  :  :   ",
    ),
    "snow": (
        "    .--.    ",
        " .-(    ).  ",
        "(___.__)__) ",
        "   *  *  *  ",
        "  *  *  *   ",
    ),
    "thunder": (
        "    .--.    ",
        " .-(    ).  ",
        "(___.__)__) ",
        "     _|     ",
        "    |       ",
    ),
    "fog": (
        " _ - _ - _  ",
        "  _ - _ -   ",
        " _ - _ - _  ",
        "  _ - _ -   ",
        " _ - _ - _  ",
    ),
    "wind": (
        "            ",
        "   ~  ~  ~  ",
        "  ~  ~  ~   ",
        "   ~  ~  ~  ",
        "            ",
    ),
}

MINI: dict[str, str] = {
    "sun": "-o-",
    "moon": "* )",
    "partly": "o_)",
    "partly-night": "*_)",
    "cloud": "(_)",
    "rain": ".:.",
    "snow": "***",
    "thunder": "(!)",
    "fog": "===",
    "wind": "~~~",
}

# 3 rows × 3 cols; only █ ▀ ▄ and space.
BLOCK_DIGITS: dict[str, tuple[str, str, str]] = {
    "0": ("█▀█", "█ █", "▀▀▀"),
    "1": (" ▀█", "  █", "  ▀"),
    "2": ("▀▀█", "█▀▀", "▀▀▀"),
    "3": ("▀▀█", "▀▀█", "▀▀▀"),
    "4": ("█ █", "▀▀█", "  ▀"),
    "5": ("█▀▀", "▀▀█", "▀▀▀"),
    "6": ("█▀▀", "█▀█", "▀▀▀"),
    "7": ("▀▀█", "  █", "  ▀"),
    "8": ("█▀█", "█▀█", "▀▀▀"),
    "9": ("█▀█", "▀▀█", "▀▀▀"),
    "-": ("   ", "▀▀▀", "   "),
}


def _normalize_icon(lines: list[str] | tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for line in list(lines)[:5]:
        if len(line) < ICON_WIDTH:
            out.append(line + " " * (ICON_WIDTH - len(line)))
        else:
            out.append(line[:ICON_WIDTH])
    while len(out) < 5:
        out.append(" " * ICON_WIDTH)
    return out


def icon_kind(text: str, is_daytime: bool) -> str:
    """Classify a forecast phrase. First keyword match wins."""
    blob = text.lower()
    if any(word in blob for word in ("thunder", "t-storm", "tstm")):
        return "thunder"
    if any(
        word in blob
        for word in ("snow", "flurries", "blizzard", "sleet", "ice", "freezing")
    ):
        return "snow"
    if any(word in blob for word in ("rain", "shower", "drizzle")):
        return "rain"
    if any(word in blob for word in ("fog", "haze", "mist", "smoke")):
        return "fog"
    if any(word in blob for word in ("windy", "breezy", "blustery")):
        return "wind"
    if any(word in blob for word in ("partly", "mostly sunny", "mostly cloudy")):
        return "partly" if is_daytime else "partly-night"
    # "mostly clear" at night reads as a clear sky (moon), not a mixed glyph.
    if "mostly clear" in blob:
        return "partly" if is_daytime else "moon"
    if any(word in blob for word in ("overcast", "cloudy", "cloud")):
        return "cloud"
    if not is_daytime and any(word in blob for word in ("clear", "fair", "sunny")):
        return "moon"
    return "sun"


def weather_icon(text: str, is_daytime: bool = True) -> list[str]:
    return _normalize_icon(ICONS[icon_kind(text, is_daytime)])


def mini_glyph(text: str, is_daytime: bool) -> str:
    glyph = MINI[icon_kind(text, is_daytime)]
    return f"{glyph:<3}"[:3]


def block_number(value: int) -> list[str]:
    """Three equal-length rows of block digits. Caller appends °."""
    chars = str(int(value))
    glyphs = [BLOCK_DIGITS[ch] for ch in chars]
    rows = [" ".join(glyph[row] for glyph in glyphs) for row in range(3)]
    return rows
