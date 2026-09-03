# ASCII UI "interest" plan

Plan only. Nothing in this document is implemented yet. It targets `main` after
PR #4 (fullscreen card + WEATHER CLI banner). The banner is out of scope and
stays exactly as it is (full / stacked / compact tiers, `banner.py` untouched).

Hard constraints carried through every section:

- Grey / white only. Allowed ANSI codes stay `{0, 1, 2, 90, 97}`.
- `--json` output and `FORECAST_PERIODS = 14` are untouched.
- Every `detailed_forecast` is shown in full. No `…` anywhere in the card.
- Card rows are all `width + 4` characters, from inner width 48 up to 200+.
- USA / NWS only. No license change. No merge.

## 1. Critique of the current screenshot

The current card is tidy, but every row uses the same recipe, so nothing pulls
the eye and nothing tells you "where you are" on the page.

1. **One typographic weight.** The temperature (`84.2°F`) is the same size as
   `humidity 62%`. The only thing that is visually "big" is the banner; the
   card below it is all body text, so the hero moment ends at the banner.
2. **The icon is decorative, not structural.** It floats next to two lines of
   text and then the block is over. Three of its five rows have nothing beside
   them.
3. **Metadata is a left-aligned list.** `wind / humidity / station / observed`
   is four label+value rows with 60 blank columns to the right on an 80-col
   terminal, and 140 blank columns on a wide one. The card is 100% width but
   only ~40% used.
4. **The forecast is prose.** Each day is a bold word, then `high 89°`, then a
   paragraph, then `low 68°`, then a paragraph. Fourteen periods produce
   fourteen near-identical blocks. There is no way to see the week's shape
   (warming, cooling, rain days) without reading every line.
5. **No rhythm between days.** The only separator is a blank line; a day
   heading looks the same as the `Forecast` section title, which looks the same
   as the place name.
6. **Wide terminals get worse, not better.** Detail paragraphs run 150+
   characters per line, which is hard to read, and everything else is empty.
7. **The icon vocabulary stops at the current block.** Forecast periods have
   no glyph, so `Chance Showers And Thunderstorms` and `Mostly Clear` look the
   same until you read them.

What works and should stay: the rounded card, the grey rule, the hanging
indents, the `label  value` meta pattern, the `·` separators, the credit line,
full untruncated detail text.

## 2. Target design

Three ideas, one system:

1. **Hero temperature in 3-row block digits** (`█ ▀ ▄` only), bold white,
   beside the existing 12×5 icon. Condition and the exact
   `84.2°F  ·  29°C` line sit under the digits. The exact string stays so
   `71.6°F` remains in the output.
2. **Stat tiles** instead of a list: dim label on top, white value below.
   Below the hero at narrow widths; beside the hero at ≥ 96 inner columns.
3. **Forecast = strip + ledger.** A "week strip" chart (one row per day, mini
   glyph, low, a `─━━━─` range bar on a shared temperature axis, high) gives
   the week's shape at a glance. Below it, the "day ledger" keeps every period
   and every full `detailed_forecast`, but each day opens with a rule that
   carries its name and lo/hi, each period gets a 3-char glyph, and on wide
   terminals day and night sit side by side.

Everything is still grey + white. Interest comes from weight (bold / dim),
shape (block digits, bars, rules) and grid, not colour.

### 2.1 Mock — 80 columns (inner 76, tier S, compact banner)

```text
                             W E A T H E R   C L I
────────────────────────────────────────────────────────────────────────────────

╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   Maple Grove, MN                                                weather-cli │
│                                                                              │
│      \   /       █▀█ █ █°                                                    │
│       .-.        █▀█ ▀▀█                                                     │
│    ― (   ) ―     ▀▀▀   ▀                                                     │
│       `-'        Clear                                                       │
│      /   \       84.2°F  ·  29°C                                             │
│                                                                              │
│   wind              humidity          observed          station              │
│   8.1 mph SE        62%               3:10 PM CDT       KMIC Minneapolis,    │
│                                                         Crystal Airport      │
│                                                                              │
│   ────────────────────────────────────────────────────────────────────────── │
│                                                                              │
│   Forecast                                                    low ━━━ high   │
│                                                                              │
│   Today      ///   68° ────────────────────────━━━━━━━━━━━━━━━━ 89°          │
│   Friday     '''   66° ─────────────────━━━━━━━━━━━━━━━━━━━━━── 84°          │
│   Saturday   o_)   63° ────────────━━━━━━━━━━━━━━━━━━━━──────── 82°          │
│   Sunday     -o-   58° ───━━━━━━━━━━━━━━━━━━━━━━━━───────────── 79°          │
│   Monday     -o-   57° ━━━━━━━━━━━━━━━━━━━━━━━━━─────────────── 78°          │
│   Tuesday    (_)   60° ──────━━━━━━━━━━━━━━━━━━━━━━━─────────── 80°          │
│   Wednesday  '''   62° ──────────━━━━━━━━━━━━━━━━━━━━━━━─────── 83°          │
│   Thursday   -o-   61° ────────━━━━━━━━━━━━━━━━━━━━━━━━━━━━──── 84°          │
│                                                                              │
│   Today ────────────────────────────────────────────────────────── 68° / 89° │
│     ///  high   89°   Slight Chance Showers And Thunderstorms  ·  10 mph SSE │
│          A slight chance of showers and thunderstorms before 4pm. Mostly     │
│          sunny, with a high near 89. South southeast wind around 10 mph.     │
│          Chance of precipitation is 20%.                                     │
│     ///  low    68°   Chance Showers And Thunderstorms  ·  5 to 10 mph SE    │
│          A chance of showers and thunderstorms between 7pm and 3am. Partly   │
│          cloudy, with a low around 68. Southeast wind 5 to 10 mph. Chance of │
│          precipitation is 40%. New rainfall amounts between a tenth and      │
│          quarter of an inch possible.                                        │
│                                                                              │
│   Friday ───────────────────────────────────────────────────────── 66° / 84° │
│     '''  high   84°   Chance Showers And Thunderstorms  ·  5 to 10 mph S     │
│          A chance of showers and thunderstorms. Mostly sunny, with a high    │
│          near 84. Chance of precipitation is 30%.                            │
│     (`.  low    66°   Mostly Clear  ·  5 mph SW                              │
│          Mostly clear, with a low around 66.                                 │
│   ⋮                                                                          │
│                                                                              │
│   NWS  ·  api.weather.gov  ·  place: OpenStreetMap Nominatim                 │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

(`⋮` marks omitted days in the mock only; the real output lists every group.)

### 2.2 Mock — 132 columns (inner 128, tier L, stacked banner above, omitted)

```text
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                  │
│   Maple Grove, MN                                                                                                    weather-cli │
│                                                                                                                                  │
│      \   /       █▀█ █ █°             wind                                        humidity                                       │
│       .-.        █▀█ ▀▀█              8.1 mph SE                                  62%                                            │
│    ― (   ) ―     ▀▀▀   ▀              observed                                    station                                        │
│       `-'        Clear                3:10 PM CDT                                 KMIC Minneapolis, Crystal Airport              │
│      /   \       84.2°F  ·  29°C                                                                                                 │
│                                                                                                                                  │
│   ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                                                                  │
│   Forecast                                                                                                        low ━━━ high   │
│                                                                                                                                  │
│   Today      ///   68° ────────────────────────━━━━━━━━━━━━━━━━ 89°                                                              │
│   Friday     '''   66° ─────────────────━━━━━━━━━━━━━━━━━━━━━── 84°                                                              │
│   Saturday   o_)   63° ────────────━━━━━━━━━━━━━━━━━━━━──────── 82°                                                              │
│   Sunday     -o-   58° ───━━━━━━━━━━━━━━━━━━━━━━━━───────────── 79°                                                              │
│   Monday     -o-   57° ━━━━━━━━━━━━━━━━━━━━━━━━━─────────────── 78°                                                              │
│   Tuesday    (_)   60° ──────━━━━━━━━━━━━━━━━━━━━━━━─────────── 80°                                                              │
│   Wednesday  '''   62° ──────────━━━━━━━━━━━━━━━━━━━━━━━─────── 83°                                                              │
│   Thursday   -o-   61° ────────━━━━━━━━━━━━━━━━━━━━━━━━━━━━──── 84°                                                              │
│                                                                                                                                  │
│   Today ────────────────────────────────────────────────────────────────────────────────────────────────────────────── 68° / 89° │
│     ///  high   89°   Slight Chance Showers And Thunderstorms  │     ///  low    68°   Chance Showers And Thunderstorms          │
│                       ·  10 mph SSE                            │                       ·  5 to 10 mph SE                         │
│          A slight chance of showers and thunderstorms before   │          A chance of showers and thunderstorms between 7pm and  │
│          4pm. Mostly sunny, with a high near 89. South         │          3am. Partly cloudy, with a low around 68. Southeast    │
│          southeast wind around 10 mph. Chance of precipitation │          wind 5 to 10 mph. Chance of precipitation is 40%. New  │
│          is 20%.                                               │          rainfall amounts between a tenth and quarter of an     │
│                                                                │          inch possible.                                         │
│                                                                                                                                  │
│   Friday ───────────────────────────────────────────────────────────────────────────────────────────────────────────── 66° / 84° │
│     '''  high   84°   Chance Showers And Thunderstorms         │     (`.  low    66°   Mostly Clear  ·  5 mph SW                 │
│                       ·  5 to 10 mph S                         │          Mostly clear, with a low around 66.                    │
│          A chance of showers and thunderstorms. Mostly sunny,  │                                                                 │
│          with a high near 84. Chance of precipitation is 30%.  │                                                                 │
│                                                                                                                                  │
│   NWS  ·  api.weather.gov  ·  place: OpenStreetMap Nominatim                                                                     │
│                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### 2.3 Mock — 52 columns (inner 48, tier XS, minimum `--width`)

```text
╭──────────────────────────────────────────────────╮
│                                                  │
│   Maple Grove, MN                    weather-cli │
│                                                  │
│      \   /       █▀█ █ █°                        │
│       .-.        █▀█ ▀▀█                         │
│    ― (   ) ―     ▀▀▀   ▀                         │
│       `-'        Clear                           │
│      /   \       84.2°F  ·  29°C                 │
│                                                  │
│   wind                   humidity                │
│   8.1 mph SE             62%                     │
│   observed               station                 │
│   3:10 PM CDT            KMIC Minneapolis,       │
│                          Crystal Airport         │
│                                                  │
│   ────────────────────────────────────────────── │
│                                                  │
│   Forecast                        low ━━━ high   │
│                                                  │
│   Today      ///   68° ────────────━━━━━━━━ 89°  │
│   Friday     '''   66° ─────────━━━━━━━━━━─ 84°  │
│   Saturday   o_)   63° ──────━━━━━━━━━━──── 82°  │
│   ⋮                                              │
```

All three mocks were generated from the rules in §3 and checked to be exactly
`width + 4` characters per row.

### 2.4 Colour roles (unchanged palette)

| Element | Codes |
| --- | --- |
| Place name, block digits, period temp, day title, strip high, `Forecast` | `BOLD WHITE` (`1;97`) |
| Condition, tile values, period summary, strip label, bar range `━` | `WHITE` (`97`) |
| Icon, mini glyphs, `high`/`low`, tile labels, rules, day lo/hi, bar track `─`, `│` gutter, brand, credits | `GREY` (`90`) |
| Exact temps line, detail paragraphs, strip low | `DIM` (`2`) |

## 3. Width breakpoints and layout rules

`W` is the inner card width (`resolve_width`), i.e. total columns − 4. Nothing
about `resolve_width` / `MIN_WIDTH = 48` / `--width` (min 52) changes.

| Tier | Inner `W` | Total | Hero | Tiles | Strip bar `B` | Ledger |
| --- | --- | --- | --- | --- | --- | --- |
| XS | 48–63 | 52–67 | icon + digits | 2 across, below hero | `W − (L+19)` ⇒ 20–35 | single column |
| S | 64–95 | 68–99 | icon + digits | 4 across, below hero | `min(W − (L+19), 40)` | single column |
| M | 96–127 | 100–131 | icon + digits | 2×2 beside hero, from col 40 | 40 | single column |
| L | ≥ 128 | ≥ 132 | icon + digits | 2×2 beside hero, from col 40 | 40 | day │ night two-column |

`layout_tier(W) -> "xs" | "s" | "m" | "l"` is a pure function so it can be
unit-tested at 63/64, 95/96, 127/128.

`dense` (terminal rows < 30) keeps its current meaning only: every blank
spacer row is dropped. It does not change the tier.

### 3.1 Header

Unchanged: `  Place, ST` bold white left, `weather-cli` grey right, wrapping
rule as today.

### 3.2 Hero (current conditions)

- Column grid: indent 2, icon 12, gap 3 → hero text starts at column 17.
- Icon: `weather_icon(kind)` 12×5, grey. Always 5 rows (stop popping blank
  trailing rows; the hero needs the height).
- Rows 0–2: `block_number(round(temperature_f))` in bold white, `°` appended to
  row 0. Digit font is 3 rows × 3 cols using only `█ ▀ ▄` and space, with a
  1-space gap between glyphs; minus is `   / ▀▀▀ /    `:

```text
█▀█  ▀█   ▀▀█  ▀▀█  █ █  █▀▀  █▀▀  ▀▀█  █▀█  █▀█
█ █   █   █▀▀  ▀▀█  ▀▀█  ▀▀█  █▀█    █  █▀█  ▀▀█
▀▀▀   ▀   ▀▀▀  ▀▀▀    ▀  ▀▀▀  ▀▀▀    ▀  ▀▀▀  ▀▀▀
```

  `temperature_f is None` → no digits; row 1 shows bold `n/a` (existing
  `_temp_label`). Width check: 3 digits + `°` + minus = 16 cols, so
  `17 + 16 = 33 ≤ 48` at XS.
- Row 3: condition, bold white. Row 4: exact `84.2°F  ·  29°C` (existing
  `_temp_label`/`_temp_c_label`), dim. If the condition needs wrapping it
  takes rows 3..k and pushes the exact line down; the hero is then taller than
  the icon and the tiles column (M/L) is zipped with blank padding.
- Hero text width: `W − 17` at XS/S; `40 − 17 − 2 = 21` at M/L (tiles start at
  col 40).

### 3.3 Stat tiles

- Items, in order, omitting missing ones exactly as today: `wind`, `humidity`,
  `observed`, `station` (`KMIC  Minneapolis, Crystal Airport` → single spaces
  between id and name). If all are missing, one tile `source` /
  `National Weather Service`.
- A tile is two rows: grey label, white value. Values longer than the tile
  width wrap with `textwrap` inside the tile (never truncated); the tile row
  height is the max over its tiles.
- XS: 2 tiles per row, tile width `(W − 2) // 2`, rows start at col 2.
- S: 4 tiles per row, tile width `(W − 2) // 4`.
- M/L: tiles start at col 40, 2 per row, tile width `(W − 40) // 2`, laid out
  on hero rows 0–3 (label, value, label, value). The last tile in a row may
  extend to the card edge (its width is `edge − start`), which is what lets a
  long station name stay on one line at 132 cols.

### 3.4 Section rule and `Forecast` title

- Grey rule unchanged.
- Title row: `  Forecast` bold white; right-aligned legend `low ━━━ high`
  (`low`/`high` grey, `━━━` white). It fits even at `W = 48`
  (`10 + 12 + 2 ≤ 48`), so it is always shown.

### 3.5 Week strip

One row per `group_forecast()` group, in order. Row template (all fixed
widths, so the bars line up):

```text
"  " + label.ljust(L) + "  " + glyph(3) + "  " + lo.rjust(4) + " " + bar(B) + " " + hi.ljust(4)
```

- `L = max(len(label) for groups)`, minimum 9 (`Wednesday`), maximum
  `W − 27`. A label longer than `L` is hard-cut to `L` without an ellipsis
  glyph (only reachable at `W = 48` with a 22+ char holiday name; the ledger
  header still prints the full name).
- `B = clamp(W − (L + 19), 8, 40)`. At `W = 76`, `L = 9` ⇒ `B = 40`; at
  `W = 48` ⇒ `B = 20`.
- Axis: `temps = all non-None period temps`; `tmin = floor(min/5)*5`,
  `tmax = ceil(max/5)*5`; if `tmax − tmin < 10` then `tmax = tmin + 10`.
  `pos(t) = round((t − tmin) / (tmax − tmin) * (B − 1))`.
- Group `hi = max(temp of daytime periods)`, `lo = min(temp of night periods)`;
  either may be `None`. Cells `[min(pos(lo), pos(hi)), max(...)]` are `━`
  (white), the rest `─` (grey). Exactly one value → a single `●` at `pos`.
  Neither → all track. `lo`/`hi` text is blank when `None`. If there are no
  temps at all, the strip is omitted.
- Glyph = `mini_glyph(kind of the daytime period, else first period)`.
- Strip label white, lo dim, hi bold white.

### 3.6 Day ledger

For each group (same grouping and heading rule as today — a single-period
group uses the period's own NWS name, e.g. `Tonight`, `Monday Night`):

**Day header** — one row:

```text
"  " + title + " " + "─" * (W − 4 − len(title) − len(lohi)) + " " + lohi
```

`lohi` is `68° / 89°`, or a single value if only one side exists, or empty
(then the rule runs to the edge). Title bold white, rule and `lohi` grey.

**Period lines** (per period, inside a column of width `cw`):

```text
"    " + glyph(3) + "  " + kind.ljust(4) + "  " + temp.rjust(4) + "   " + summary
```

- Prefix is 22 columns; `summary` wraps at `cw − 22` with a 22-col hang.
- Wind rule: summary is `short_forecast  ·  wind` if that fits on the first
  line; otherwise wrap `short_forecast` alone and put `·  wind` on its own
  hanging line. No mid-phrase breaks like `5  ·  to 10 mph`.
- Detail: `detailed_forecast` at indent 9, width `cw − 9`, dim, every line
  (no `max_lines`, no ellipsis), omitted when it equals the short forecast
  (today's rule).
- Glyph grey, kind grey, temp bold white, summary white.

**Columns**

- XS/S/M: `cw = W`, periods stacked.
- L: if the group has exactly one daytime and one night period, render them as
  two columns `[day, night]`: `C = (W − 3) // 2`, `R = W − C − 3`, joined with
  a grey `" │ "`; shorter column padded with blank rows. Any other group
  shape (lone `Tonight`, `Today / This Afternoon / Tonight` triples) is stacked
  full-width even at L.
- Blank spacer row between groups unless `dense`.

### 3.7 Credits

Unchanged.

### 3.8 Icon kinds and glyphs

Introduce `icon_kind(text, is_daytime) -> str`, the single classifier used by
both the 12×5 icon and the 3-char mini glyph. Evaluation order (first match
wins):

| kind | keywords |
| --- | --- |
| `thunder` | thunder, t-storm, tstm |
| `snow` | snow, flurries, blizzard, sleet, ice, freezing |
| `rain` | rain, shower, drizzle |
| `fog` | fog, haze, mist, smoke |
| `wind` | windy, breezy, blustery |
| `partly` / `partly-night` | partly, mostly sunny, mostly cloudy, mostly clear (night → `partly-night`) |
| `cloud` | overcast, cloudy, cloud |
| `moon` | clear, fair, sunny when `not is_daytime` |
| `sun` | default |

Note `mostly cloudy` currently falls to `cloud`; moving it to `partly` is a
deliberate change so partly/mostly cloudy read as "some sun/moon".

Mini glyphs (3 ASCII chars, echoing the big icons so the vocabulary is one
family):

| kind | glyph |
| --- | --- |
| `sun` | `-o-` |
| `moon` | `` (`. `` |
| `partly` | `o_)` |
| `partly-night` | `` `_) `` |
| `cloud` | `(_)` |
| `rain` | `'''` |
| `snow` | `***` |
| `thunder` | `///` |
| `fog` | `-_-` |
| `wind` | `~~~` |

Big icons stay 12×5 (tests assert this). Redraw for presence within that box:
`moon` gains two `*` stars, `partly-night` is the moon peeking over the cloud,
`thunder` swaps the middle `/ / /` row for a bolt `' /_/ '`, `wind` is a new
`~ ~ ~` icon. Sun stays as is.

## 4. File-by-file change list

### `src/weather_cli/glyphs.py` (new)

- `icon_kind(text: str, is_daytime: bool) -> str`
- `ICONS: dict[str, tuple[str, ...]]` (12×5 per kind), `weather_icon(text, is_daytime=True)` keeps its
  current signature and returns `_normalize_icon(ICONS[icon_kind(...)])`.
- `MINI: dict[str, str]`, `mini_glyph(text, is_daytime) -> str` (always 3
  chars).
- `BLOCK_DIGITS: dict[str, tuple[str, str, str]]`,
  `block_number(value: int) -> list[str]` (3 rows, equal length, `°`
  appended by the caller).
- Move `ICON_WIDTH` and `_normalize_icon` here.

### `src/weather_cli/display.py`

- Import and re-export `weather_icon`, `mini_glyph`, `icon_kind`,
  `block_number` from `glyphs` (tests import `weather_icon` from `display`).
- Add `layout_tier(width) -> str` with the §3 thresholds.
- Add `_columns(cells: list[list[str]], widths: list[int], gutter: str)` —
  generic zip-and-pad helper used by tiles, hero+tiles and the L ledger.
- Add `_tiles(current, loc, tier, width, color) -> list[str]` (§3.3).
- Replace `_current_block` with `_hero_block(report, width, tier, color, dense)`
  (§3.2 + tiles placement).
- Add `temp_axis(periods) -> tuple[int, int]`, `temp_bar(lo, hi, axis, B) -> str`,
  `group_hi_lo(periods) -> tuple[int | None, int | None]`, and
  `_strip_block(groups, width, color, dense)` (§3.5). `temp_bar` returns
  plain text of exactly `B` cells; colouring is done per cell class by the
  caller so the pure function is testable.
- Add `_day_header(title, lo, hi, width, color)` (§3.6).
- Rewrite `_period_lines(period, col_width, color)` with the 22-col prefix,
  glyph, wind rule and indent-9 detail.
- Rewrite `_forecast_block(report, width, tier, color, dense)` to emit title
  + legend, strip, then ledger with the L two-column rule.
- `render_ascii`: compute `tier = layout_tier(inner)` once and pass it down.
  Banner call and `banner_mode` spacing stay exactly as they are.
- Delete `_wrap_text`'s `max_lines` branch (the only ellipsis-producing code
  path besides `_pad`/`_truncate`, which remain as last-resort guards).
- Keep `_meta_row`/`_meta_wrapped` only if still used; otherwise delete.

### `src/weather_cli/banner.py`

- No change.

### `src/weather_cli/cli.py`

- No change. (`--width` semantics, `--no-banner`, `--json` untouched.)

### `src/weather_cli/models.py`, `client.py`, `http.py`, `place.py`

- No change. JSON shape and `FORECAST_PERIODS` untouched.

### `README.md`

- Update "What you get": describe hero digits, tiles, week strip, day ledger,
  and add the width-tier table from §3 next to the existing banner-tier list.
- Bump nothing else. (Version bump in `pyproject.toml` to `0.3.0` is optional
  and can be a separate commit.)

### `tests/test_weather.py`

- See §5.

## 5. Test updates

Existing tests that must keep passing unchanged:

- `test_ascii_grey_white_not_rainbow` (`codes ⊆ {0,1,2,90,97}`).
- `test_ascii_narrow_width_keeps_box` (W = 50, uniform rows ≤ 56).
- `test_weather_icons_are_balanced` (12×5) — extend its sample list with
  `("Windy", True)`, `("Partly Cloudy", False)`.
- `test_width_not_clamped`, `test_no_banner_and_width_flags`,
  `test_width_below_minimum_rejected`, all `BannerTests`, all JSON tests.
- `test_ascii_includes_current_and_forecast`: all current asserts still hold
  (`71.6°F`, `Clear`, `Tonight`, `Forecast`, `wind`, `humidity`, `KMSP`,
  `high`, `low`, full detail sentences). Add: `assertIn("83°", art)`,
  `assertIn("68° / 83°", art)` (Wednesday header), `assertIn("-o-", art)`
  or `assertIn("(`.", art)` for glyph presence, and
  `assertIn("low ━━━ high", art)`.

Tests that need a helper change:

- `test_full_detailed_forecast_no_ellipsis` iterates widths
  `(48, 60, 76, 100, 140, 200)`. At 140 and 200 the L tier puts Saturday's
  `LONG_DETAIL` in the left column next to Saturday Night. Add
  `_column_texts(art) -> tuple[str, str]` that, for each card row, splits the
  inner text on the interior `" │ "` (rows without it go entirely to the left
  accumulator) and returns squeezed left/right strings. Assert
  `LONG_DETAIL in left` for `layout_tier(width) == "l"`, else the existing
  `_squeezed` check. Keep `assertNotIn("…", art)` and the uniform-row-length
  assert for every width.

New tests:

- `test_layout_tiers`: 48/63 → `xs`, 64/95 → `s`, 96/127 → `m`, 128/200 → `l`.
- `test_block_digits`: every entry in `BLOCK_DIGITS` is 3 rows × 3 cols using
  only `█▀▄ `; `block_number(84)`, `block_number(-12)`, `block_number(105)`
  return 3 equal-length rows; `render_ascii` for a report with
  `temperature_f=None` shows `n/a` and no digit rows.
- `test_icon_kind_and_mini_glyph`: table-driven —
  `("Chance Showers And Thunderstorms", True) → thunder`,
  `("Mostly Clear", False) → moon`, `("Partly Cloudy", False) → partly-night`,
  `("Mostly Cloudy", True) → partly`, `("Windy", True) → wind`,
  `("Sunny", True) → sun`; every mini glyph is exactly 3 chars and ASCII.
- `test_temp_axis_and_bar`: axis rounds outward to 5s and widens to ≥ 10;
  `temp_bar` returns exactly `B` cells; range cells are `━`, single value is
  one `●`, both-None is all `─`; `lo > hi` (inverted) still draws
  `min..max`.
- `test_group_hi_lo`: `Today + Tonight` → `(hi, lo)`; lone `Tonight` →
  `(None, lo)`; `Today / This Afternoon / Tonight` triple → `(max day, lo)`.
- `test_strip_rows_align`: at W = 76 every strip row's `━`/`─` bar spans the
  same columns (extract the bar with a regex and compare `start` and `len`).
- `test_two_column_ledger_wide`: W = 140 → the Saturday rows contain
  `" │ "`, and `Chance Showers` and `Showers Likely` appear on the same row;
  `Tonight` (lone night) rows contain no interior `│`.
- `test_single_column_below_l`: W = 100 → no card row contains an interior
  `│`.
- `test_tiles_wrap_long_station`: a 60-char station name at W = 64 → no
  `…`, uniform rows, name fully present in `_squeezed(art)`.
- `test_summary_wind_never_splits`: at W = 48 with
  `short_forecast="Slight Chance Showers And Thunderstorms"`,
  `wind="5 to 10 mph SE"`, the output contains `·  5 to 10 mph SE` on one
  row and never `5  ·  to`.
- `test_dense_drops_spacers`: `render_ascii(rows=20)` has fewer rows than
  `rows=50` and contains no blank card row between `Forecast` and the first
  strip row.
- `test_holiday_label_hard_cut_no_ellipsis`: W = 48 with a
  `Washington's Birthday` period → uniform rows, no `…`, full name present in
  the ledger header.

## 6. Acceptance checklist

- [ ] `PYTHONPATH=src python3 -m unittest discover -s tests -v` passes; test
      count ≥ 22 + new tests.
- [ ] `weather-cli --json "Seattle, WA"` byte-for-byte equal to `main` for the
      same fixtures (keys `ok, source, location, current, forecast`; 14
      periods).
- [ ] Banner: `--width 200` full art, `COLUMNS=150` stacked, `COLUMNS=80`
      compact; `--no-banner` hides it. `banner.py` diff is empty.
- [ ] Palette: `grep -o $'\e\[[0-9;]*m' | sort -u` on coloured output yields
      only `0`, `1`, `2`, `90`, `97`.
- [ ] For `--width` in `52 56 64 68 80 96 100 128 132 160 200`: every card row
      has identical length; no `…` anywhere; every fixture
      `detailed_forecast` string is present in the column-aware squeeze.
- [ ] 80-col terminal (`COLUMNS=80`): output matches §2.1 structure — digits,
      4 tiles across, 8 strip rows with aligned bars, day headers with
      `lo / hi`, glyph per period.
- [ ] ≥ 132-col terminal: tiles beside the hero, day/night two-column ledger,
      lone `Tonight` full-width.
- [ ] 52-col terminal: §2.3 structure, 2 tiles across, bar width 20.
- [ ] `LINES=20` (dense): no spacer rows, everything else identical.
- [ ] `temperature_f=None`, empty forecast, forecast without any temps: no
      exception, card still uniform.
- [ ] Manual check on macOS Terminal.app and iTerm2 with Menlo / SF Mono /
      JetBrains Mono: `█ ▀ ▄ ─ ━ ● │` all render single-width and aligned.
- [ ] README "What you get" and width-tier table updated; `--help` unchanged.
- [ ] No changes to `LICENSE`, `client.py`, `models.py`, `cli.py`.

## 7. Risks

- **Glyph width in terminals.** `█ ▀ ▄ ━ ●` are East-Asian-Ambiguous like the
  `─ │ ╭ ·` already in use; terminals with "ambiguous = wide" enabled would
  break both the current and the new card. Mitigation: everything else in the
  card already assumes narrow; document it; do not add emoji or U+26xx symbols
  (`⚡` is `Emoji_Presentation` and renders 2 columns).
- **Font coverage for block elements.** Menlo, SF Mono, Monaco, JetBrains
  Mono, Fira Code all include U+2580–259F; a font that lacks them falls back
  to a system font and may look slightly misaligned but keeps width 1.
  Mitigation: digits only use `█ ▀ ▄` (the three most common block glyphs), not
  quadrant blocks.
- **Column-interleaved text in tests.** Any assertion that squeezes the whole
  card into one string breaks at tier L; §5's `_column_texts` helper is
  required before the L tier lands. Land the helper and the tier in the same
  commit.
- **Vertical length.** The strip adds up to 9 rows; a 14-period forecast card
  already exceeds 24 rows. Fullscreen users are fine; `dense` mitigates on
  short terminals. If it matters later, a `--no-strip` flag is a trivial
  follow-up (not in this scope).
- **Holiday / long NWS period names.** `Washington's Birthday` (21 chars)
  pushes `L` up and shrinks `B`; at `W = 48` it is hard-cut in the strip. The
  ledger header always shows the full name. Covered by a test.
- **Groups with 3+ periods** (`Today`, `This Afternoon`, `Tonight`). Two-column
  layout is only for exactly day+night; triples stack. `group_hi_lo` takes
  max/min so the strip stays correct.
- **`mostly cloudy` reclassified to `partly`.** Changes which 12×5 icon shows
  for that phrase; no test asserts the old mapping, but call it out in the PR.
- **Hero text width at M/L is 21 columns.** Long `textDescription` values
  (`Thunderstorms and Rain Fog/Mist`) wrap to two rows and push the exact-temp
  line to row 5; tiles are zipped with padding so rows stay uniform. Worth a
  fixture.
- **Scope creep into the banner.** None of the above touches `banner.py`; if
  an implementer is tempted to restyle the compact title to match the new
  legend, resist — the banner tiers have their own SHA-pinned tests.
