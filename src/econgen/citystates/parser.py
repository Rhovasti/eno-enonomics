"""Parse citystate ``.md`` profiles into ``CitystateSpec`` records.

Each profile (at ``Eno-Worldbuilder2/citystates for economic profiles/``) is a
YAML-ish frontmatter block plus a markdown body. The frontmatter has two
generations with field-name splits (``founded_cycle`` vs ``founded``;
``latitude/longitude`` vs ``coordinates: [lat, lon]``) and wikilink values that
break a strict YAML parse, so we parse line-by-line with regexes.
"""

import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

# Growth-rate prior (decimal fraction) by normalized temporal_state, used when a
# profile has no explicit "Growth Rate: X% annually" line (~half of them).
# Derived from the audit's per-state growth ranges.
GROWTH_PRIOR_BY_STATE = {
    "Dawn": 0.035,
    "Day": 0.020,
    "Dusk": 0.015,
    "Noon": -0.005,
    "Night": -0.003,
    "Drifters": 0.010,
    "Wildlands": 0.020,
    "Winds": 0.008,
    "Symbiotic Decline": -0.010,
    "Dwellers": 0.005,
    "Autotrophic Founder": 0.015,
}
DEFAULT_GROWTH = 0.010
DEFAULT_TEMPORAL_STATE = "Day"
# Synthetic values for stub cities (e.g. Valsang) missing founding/coords.
SYNTHETIC_FOUNDED_CYCLE = 150

_FRONTMATTER_RE = re.compile(r"^---\s*$", re.MULTILINE)
_KV_RE = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
_GROWTH_RE = re.compile(r"Growth Rate[^:\n]*:\s*([+-]?\d+(?:\.\d+)?)\s*%")
_FOUNDED_RE = re.compile(r"^[Ff]ounded(?:\s+in\s+[Cc]ycle)?[:\s]+(\d+)")


class CitystateSpec(BaseModel):
    """One citystate's parsed profile, ready for endowment inference + simulation."""

    name: str
    founded_cycle: int = Field(ge=0, le=998)
    population: int = Field(ge=0)
    growth_rate: float
    temporal_state: str
    valley: str
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    infrastructure: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    state: str = ""
    source_file: str = ""


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body) from a profile file's text."""
    matches = list(_FRONTMATTER_RE.finditer(text))
    if len(matches) >= 2:
        return text[matches[0].end() : matches[1].start()], text[matches[1].end() :]
    return "", text


def _parse_list(value: str) -> List[str]:
    """Parse a ``[a, b, c]`` bracket value into a list of trimmed strings."""
    inner = value.strip().strip("[]")
    if not inner:
        return []
    return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]


def _normalize_temporal_state(raw: str) -> str:
    """Collapse e.g. 'Day (peak efficiency, maximum prosperity)' -> 'Day'."""
    base = raw.split("(", 1)[0].strip()
    if not base:
        base = raw.strip()
    return base.title()


def _normalize_valley(raw: str) -> str:
    """Extract the valley name from formats like:
    ``[[The Four Valleys#Night Valley]]``, ``[[The Four Valleys|Dawn Valley]]``,
    ``Dawn``, ``[[Dusk Valley]]`` -> ``Night`` / ``Dawn`` / ``Dusk``.
    """
    for sep in ("#", "|"):
        if sep in raw:
            raw = raw.split(sep)[-1]
    raw = raw.replace("[", "").replace("]", "").replace("Valley", "").strip()
    if "Four" in raw:  # generic "[[The Four Valleys]]" with no specific valley
        return "Four Valleys"
    return raw or "unknown"


def _parse_frontmatter(block: str) -> dict:
    """Parse frontmatter lines into a raw dict (values are strings or lists)."""
    data: dict = {}
    for line in block.splitlines():
        m = _KV_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        # A YAML flow list is "[a, b]"; a wikilink is "[[...]]" -> keep as string.
        if value.startswith("[") and not value.startswith("[["):
            data[key] = _parse_list(value)
        else:
            data[key] = value.strip("\"'")
    return data


def _coords(data: dict, name: str) -> tuple[float, float]:
    """Resolve (lat, lon) from latitude/longitude or coordinates: [lat, lon]."""
    if "latitude" in data and "longitude" in data:
        return float(data["latitude"]), float(data["longitude"])
    if "coordinates" in data and isinstance(data["coordinates"], list):
        c = data["coordinates"]
        if len(c) >= 2:
            return float(c[0]), float(c[1])
    # Stub (e.g. Valsang): synthetic at the equator/prime meridian.
    return 0.0, 0.0


def parse_citystate(path: Path) -> CitystateSpec:
    """Parse a single citystate ``.md`` profile into a ``CitystateSpec``."""
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    data = _parse_frontmatter(frontmatter)
    name = data.get("title", path.stem)

    founded = SYNTHETIC_FOUNDED_CYCLE
    if "founded_cycle" in data:
        founded = int(data["founded_cycle"])
    elif "founded" in data:
        founded = int(data["founded"])

    temporal_state = _normalize_temporal_state(data.get("temporal_state", DEFAULT_TEMPORAL_STATE))

    growth_match = _GROWTH_RE.search(body)
    if growth_match:
        growth_rate = float(growth_match.group(1)) / 100.0
    else:
        growth_rate = GROWTH_PRIOR_BY_STATE.get(temporal_state, DEFAULT_GROWTH)

    lat, lon = _coords(data, name)
    elevation = float(data["elevation"]) if "elevation" in data else None

    return CitystateSpec(
        name=name,
        founded_cycle=founded,
        population=int(data.get("population", 0)),
        growth_rate=growth_rate,
        temporal_state=temporal_state,
        valley=_normalize_valley(data.get("valley", "")),
        latitude=lat,
        longitude=lon,
        elevation=elevation,
        infrastructure=data.get("infrastructure", [])
        if isinstance(data.get("infrastructure"), list)
        else [],
        tags=data.get("tags", []) if isinstance(data.get("tags"), list) else [],
        state=data.get("state", ""),
        source_file=path.name,
    )


def load_citystates(directory) -> List[CitystateSpec]:
    """Load every ``*.md`` citystate profile under ``directory`` (skips sidecars)."""
    directory = Path(directory)
    return [
        parse_citystate(path)
        for path in sorted(directory.glob("*.md"))
        if not path.name.endswith(":Zone.Identifier")
    ]


__all__ = [
    "CitystateSpec",
    "parse_citystate",
    "load_citystates",
    "GROWTH_PRIOR_BY_STATE",
]
