"""WEATHER CLI banner art and terminal-width modes."""

from __future__ import annotations

BANNER_WIDTH = 177
BANNER_SHA256 = "ca68821387f71bce0b82c9ed221a87e498e488ca777eefd097422a9a5bf7f9f6"
COMPACT_TITLE = "W E A T H E R   C L I"

# Quoted literals keep trailing spaces (lines 1-9 are 177 chars; line 10 is 176).
BANNER_LINES: tuple[str, ...] = (
    "`8.`888b                 ,8' 8 8888888888            .8.    8888888 8888888888 8 8888        8 8 8888888888   8 888888888o.                 ,o888888o.    8 8888          8 8888 ",
    " `8.`888b               ,8'  8 8888                 .888.         8 8888       8 8888        8 8 8888         8 8888    `88.               8888     `88.  8 8888          8 8888 ",
    "  `8.`888b             ,8'   8 8888                :88888.        8 8888       8 8888        8 8 8888         8 8888     `88            ,8 8888       `8. 8 8888          8 8888 ",
    "   `8.`888b     .b    ,8'    8 8888               . `88888.       8 8888       8 8888        8 8 8888         8 8888     ,88            88 8888           8 8888          8 8888 ",
    "    `8.`888b    88b  ,8'     8 888888888888      .8. `88888.      8 8888       8 8888        8 8 888888888888 8 8888.   ,88'            88 8888           8 8888          8 8888 ",
    "     `8.`888b .`888b,8'      8 8888             .8`8. `88888.     8 8888       8 8888        8 8 8888         8 888888888P'             88 8888           8 8888          8 8888 ",
    "      `8.`888b8.`8888'       8 8888            .8' `8. `88888.    8 8888       8 8888888888888 8 8888         8 8888`8b                 88 8888           8 8888          8 8888 ",
    "       `8.`888`8.`88'        8 8888           .8'   `8. `88888.   8 8888       8 8888        8 8 8888         8 8888 `8b.               `8 8888       .8' 8 8888          8 8888 ",
    "        `8.`8' `8,`'         8 8888          .888888888. `88888.  8 8888       8 8888        8 8 8888         8 8888   `8b.                8888     ,88'  8 8888          8 8888 ",
    "         `8.`   `8'          8 888888888888 .8'       `8. `88888. 8 8888       8 8888        8 8 888888888888 8 8888     `88.               `8888888P'    8 888888888888  8 8888",
)


def banner_mode(columns: int) -> str:
    """Pick full, stacked, or compact art from terminal columns."""
    if columns >= BANNER_WIDTH:
        return "full"
    if columns >= 127:
        return "stacked"
    return "compact"


def _center(text: str, columns: int) -> str:
    pad = max((int(columns) - len(text)) // 2, 0)
    return (" " * pad) + text


def _padded_lines() -> list[str]:
    return [line.ljust(BANNER_WIDTH) for line in BANNER_LINES]


def render_banner(columns: int, card_width: int | None = None) -> list[str]:
    """Render banner lines for a terminal width. Art sits above the card."""
    mode = banner_mode(columns)
    padded = _padded_lines()
    if mode == "full":
        return [_center(line, columns) for line in padded]
    if mode == "stacked":
        weather = [_center(line[0:125], columns) for line in padded]
        cli = [_center(line[136:BANNER_WIDTH], columns) for line in padded]
        return weather + cli
    span = card_width if card_width is not None else columns
    return [_center(COMPACT_TITLE, span), "─" * max(int(span), 1)]
