# weather-cli

A easy to use, fun weather CLI for agents and you.

Type a US city and state, get current conditions and a multi-day forecast in a
quiet grey/white ASCII panel. Add `--json` when a script or agent needs
structured data.

v1 is **USA only**. Weather data comes from the
[National Weather Service](https://www.weather.gov/) (`api.weather.gov`).
Places are geocoded with [OpenStreetMap Nominatim](https://nominatim.org/)
(no API key).

## Install on macOS

You need Python 3.9+ and [Homebrew](https://brew.sh) (Apple Silicon and Intel
are both fine). Copy and paste the commands as written — no `$` in front.

**One easy path** — a script that installs [pipx](https://pipx.pypa.io/) via
Homebrew if needed, runs `pipx ensurepath`, and retries with `--backend pip`
when pipx's `uv` is too old:

```bash
curl -fsSL https://raw.githubusercontent.com/eddiehorihan/weather-cli/main/scripts/install-macos.sh | bash
```

Already cloned this repo? Same installer, from the repo root:

```bash
bash scripts/install-macos.sh
```

The installer does not install Homebrew for you. If `weather-cli` is missing
after it finishes, run `pipx ensurepath`, then open a new terminal.

```bash
weather-cli --help
```

### Manual pipx

```bash
brew install pipx
pipx ensurepath
pipx install git+https://github.com/eddiehorihan/weather-cli.git
```

If pipx errors that it needs a newer `uv` (for example `uv>=0.9.17` but yours
is older), retry with the pip backend — `--backend` goes after `install`:

```bash
pipx install git+https://github.com/eddiehorihan/weather-cli.git --backend pip
```

To reinstall, put `--force` after `install` (not before `pipx` and not after
the URL only):

```bash
pipx install --force git+https://github.com/eddiehorihan/weather-cli.git --backend pip
```

Do not use `python3 -m pip install --user` on Homebrew Python. That hits
PEP 668 (`externally-managed-environment`). pipx is the supported path.

No API keys or secrets. The client sends a `User-Agent` identifying this app,
which NWS and Nominatim both require.

## How to run

Interactive (default) — just run it and type a place:

```text
weather-cli

  weather-cli  ·  USA weather from the National Weather Service
  City and state (e.g. Minneapolis, MN): Minneapolis, MN
```

Skip the prompt by passing a place:

```bash
weather-cli "Minneapolis, MN"
weather-cli --city Austin --state TX
```

### `--json` for agents

Stable keys: `ok`, `source`, `location`, `current`, `forecast`.

```bash
weather-cli --json "Seattle, WA"
```

```json
{
  "ok": true,
  "source": "nws",
  "location": {
    "query": "Seattle, WA",
    "city": "Seattle",
    "state": "WA",
    "display_name": "Seattle, King County, Washington, United States",
    "latitude": 47.6038,
    "longitude": -122.3301,
    "timezone": "America/Los_Angeles"
  },
  "current": {
    "condition": "Cloudy",
    "temperature_f": 62.6,
    "temperature_c": 17.0,
    "wind_mph": 5.0,
    "wind_direction_degrees": 200,
    "humidity_percent": 80,
    "station_id": "KBFI",
    "station_name": "Seattle, Seattle Boeing Field",
    "observed_at": "2026-09-02T03:53:00+00:00"
  },
  "forecast": [
    {
      "name": "Tonight",
      "is_daytime": false,
      "temperature_f": 55,
      "temperature_unit": "F",
      "wind": "5 mph S",
      "short_forecast": "Cloudy",
      "detailed_forecast": "Cloudy, with a low around 55."
    }
  ]
}
```

Numbers above are examples. Real values come from NWS at request time.

If something fails and you passed `--json`, stdout is still JSON:

```json
{ "ok": false, "error": "Couldn't find 'Atlantis, ZZ' in the USA. Try City, ST — like Minneapolis, MN." }
```

Non-interactive runs (CI, agents) should pass a place. An empty prompt would
hang; instead the CLI exits with an example invocation.

```bash
weather-cli --no-color "Denver, CO"
weather-cli --no-banner "Denver, CO"
weather-cli --width 80 "Denver, CO"
```

`--width N` is the total card width in columns (minimum 52). Without it, the
card fills the terminal (`columns - 1`). `--no-banner` hides the WEATHER CLI
art that sits above the card.

Banner size follows terminal columns:

- **>= 177** — full 10-line WEATHER CLI art, centered
- **>= 127** — stacked WEATHER then CLI (20 lines)
- **narrower** — compact `W E A T H E R   C L I` plus a grey rule

## What you get

1. **Hero** — 12×5 condition icon beside 3-row block digits (`█ ▀ ▄`), the
   condition, and the exact temperature (`71.6°F · 22°C`) so tenths stay visible
2. **Stat tiles** — wind, humidity, observed time, and station as a 2- or 4-wide
   grid (beside the hero once the card is wide enough)
3. **Week strip** — one row per day: mini glyph, low, a shared-axis `─━━━─`
   range bar, high
4. **Day ledger** — every NWS period with a glyph and the full official
   `detailed_forecast` (no ellipsis). On wide terminals, day and night sit
   side by side

Card layout follows inner width (total columns − 4):

| Inner width | Total | Hero / tiles | Forecast ledger |
| --- | --- | --- | --- |
| 48–63 | 52–67 | icon + digits; 2 tiles below | single column |
| 64–95 | 68–99 | icon + digits; 4 tiles below | single column |
| 96–127 | 100–131 | tiles beside the hero | single column |
| ≥ 128 | ≥ 132 | tiles beside the hero | day │ night columns |

No severe-alerts product in v1.

## Develop / test

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
