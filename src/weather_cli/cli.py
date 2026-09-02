"""weather-cli entry point: interactive by default, flags for agents."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from weather_cli import __version__
from weather_cli.client import fetch_report
from weather_cli.display import render_ascii, render_json, render_json_error
from weather_cli.http import JsonFetcher, fetch_json
from weather_cli.place import Place, parse_place

USAGE_EXAMPLES = """
Examples:
  weather-cli
  weather-cli "Minneapolis, MN"
  weather-cli --city Austin --state TX
  weather-cli --json "Seattle, WA"
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-cli",
        description=(
            "Show current conditions and a multi-day USA forecast from the "
            "National Weather Service. With no place, asks you for a city and state."
        ),
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "place",
        nargs="*",
        help='City and state, like Minneapolis, MN (optional — you will be prompted)',
    )
    parser.add_argument("--city", help="US city name")
    parser.add_argument("--state", help="US state abbreviation or name, like MN or Minnesota")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print stable machine-readable JSON (current + forecast) instead of ASCII",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in the ASCII view",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"weather-cli {__version__}",
    )
    return parser


def resolve_place(args: argparse.Namespace, stdin, stdout) -> Place:
    if args.city or args.state:
        city = (args.city or "").strip()
        state = (args.state or "").strip()
        if args.place and not city:
            city = " ".join(args.place).strip()
        if not city:
            raise ValueError("Need a city. Example: weather-cli --city Minneapolis --state MN")
        return parse_place(f"{city}, {state}" if state else city)

    if args.place:
        return parse_place(" ".join(args.place))

    if stdin.isatty():
        stdout.write("\n")
        stdout.write("  weather-cli  ·  USA weather from the National Weather Service\n")
        stdout.write("  City and state (e.g. Minneapolis, MN): ")
        stdout.flush()
        typed = stdin.readline()
        stdout.write("\n")
    else:
        typed = stdin.readline()

    text = (typed or "").strip()
    if not text:
        raise ValueError(
            "City and state required when not running interactively.\n"
            "  weather-cli \"Minneapolis, MN\"\n"
            "  weather-cli --city Austin --state TX\n"
            "  weather-cli --json \"Seattle, WA\""
        )
    return parse_place(text)


def wants_color(args: argparse.Namespace, stdout) -> bool:
    if args.no_color or args.json:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return bool(stdout.isatty())


def run(
    argv: Sequence[str] | None = None,
    *,
    stdin=None,
    stdout=None,
    stderr=None,
    fetch: JsonFetcher = fetch_json,
) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr

    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0

    as_json = bool(args.json)
    try:
        place = resolve_place(args, stdin=stdin, stdout=stdout)
        report = fetch_report(place, fetch=fetch)
    except (ValueError, RuntimeError) as exc:
        message = str(exc)
        if as_json:
            stdout.write(render_json_error(message) + "\n")
        else:
            stderr.write(f"error: {message}\n")
        return 1

    if as_json:
        stdout.write(render_json(report) + "\n")
    else:
        color = wants_color(args, stdout)
        stdout.write(render_ascii(report, color=color) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)
