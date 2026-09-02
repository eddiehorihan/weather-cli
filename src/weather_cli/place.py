"""Parse human city/state input into a geocodable place."""

from __future__ import annotations

from dataclasses import dataclass

US_STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
    "GU": "Guam",
    "AS": "American Samoa",
    "MP": "Northern Mariana Islands",
}

_NAME_TO_ABBR = {name.lower(): abbr for abbr, name in US_STATE_NAMES.items()}


@dataclass(frozen=True)
class Place:
    city: str
    state: str | None = None

    def query_string(self) -> str:
        if self.state:
            return f"{self.city}, {self.state}"
        return self.city


def _require_known_state(state: str) -> str:
    if state not in US_STATE_NAMES:
        raise ValueError(
            f"Unknown US state {state!r}. Use a 2-letter code like MN."
        )
    return state


def normalize_state(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in US_STATE_NAMES:
        return upper
    return _NAME_TO_ABBR.get(text.lower(), text)


def parse_place(text: str) -> Place:
    """Parse 'Minneapolis, MN', 'Minneapolis MN', or a city-only string."""
    raw = " ".join(text.replace(",", " , ").split())
    if not raw:
        raise ValueError("Enter a US city and state, like Minneapolis, MN.")

    if "," in raw:
        city_part, state_part = raw.split(",", 1)
        city = city_part.replace(",", " ").strip()
        state = normalize_state(state_part.replace(",", " ").strip())
        if not city:
            raise ValueError("Enter a US city and state, like Minneapolis, MN.")
        return Place(city=city, state=_require_known_state(state) if state else None)

    parts = raw.split()
    if len(parts) >= 2:
        last = parts[-1]
        last_is_state = last.upper() in US_STATE_NAMES or last.lower() in _NAME_TO_ABBR
        if last_is_state:
            return Place(city=" ".join(parts[:-1]), state=_require_known_state(normalize_state(last)))
        if len(parts) >= 3:
            last_two = " ".join(parts[-2:])
            if last_two.lower() in _NAME_TO_ABBR:
                return Place(
                    city=" ".join(parts[:-2]),
                    state=_require_known_state(normalize_state(last_two)),
                )
    return Place(city=raw, state=None)
