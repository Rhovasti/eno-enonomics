"""Infer resource endowments for a citystate from its ``.md`` geography.

The ``.md`` profiles carry no endowment data, so we derive the capacity-driver
keys the production rules expect (mundane + Eno fantastical) from geography:
elevation, valley, temporal_state, infrastructure, tags, and longitude. This is
the ``.md`` analog of ``io_geojson._infer_fantastical_endowments``.
"""

from .parser import CitystateSpec

# Industrial-capacity prior by temporal_state (peak economies > stagnant > crisis).
INDUSTRIAL_BY_STATE = {
    "Day": 0.6,
    "Noon": 0.5,
    "Dawn": 0.4,
    "Dusk": 0.3,
    "Winds": 0.3,
    "Autotrophic Founder": 0.3,
    "Night": 0.2,
    "Drifters": 0.2,
    "Wildlands": 0.2,
    "Symbiotic Decline": 0.2,
    "Dwellers": 0.2,
}

# Curated periodic elements (see fantastical.py) for deposit specialization.
_ELEMENTS = ("feron", "cunu", "charon", "plon", "suhra", "sirael", "aru", "sira")


def _stable_hash(text: str) -> int:
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) % 0x80000000
    return h


def _pick_elements(name: str) -> list[str]:
    """Pick 1-2 element deposits deterministically per city (stable specialization)."""
    h = _stable_hash(name)
    count = 1 + (h % 2)
    chosen: list[str] = []
    seed = h
    while len(chosen) < count:
        seed = (seed * 1103515245 + 12345) % 2147483647
        element = _ELEMENTS[seed % len(_ELEMENTS)]
        if element not in chosen:
            chosen.append(element)
    return chosen


def infer_endowments(spec: CitystateSpec) -> dict[str, float]:
    """Derive the capacity-driver endowments for one citystate.

    Returns a ``{driver_key: magnitude}`` dict whose keys match the
    ``ProductionRule.capacity_driver`` strings.
    """
    signals = {s.lower() for s in (list(spec.infrastructure) + list(spec.tags))}
    endowments: dict[str, float] = {
        # Universal basics so staples (food/tools/wood) are locally producible.
        "agriculture": 0.5,
        "craftsmanship": 0.4,
        "general_labor": 0.4,
        "skilled_labor": 0.5,
        "forestry": 0.3,
    }

    # Mining from elevation (mountains) or explicit mining/mountain tags.
    if spec.elevation is not None and spec.elevation > 500:
        endowments["mining_potential"] = 0.6
    elif spec.elevation is not None and spec.elevation > 200:
        endowments["mining_potential"] = 0.3
    if "mine" in signals or "mountain" in signals or "mountain-city" in signals:
        endowments["mining_potential"] = max(endowments.get("mining_potential", 0.0), 0.6)

    # Coastal / port trade.
    if "port" in signals or "coastal" in signals or "harbor" in signals:
        endowments["fishing"] = 0.8
        endowments["trade_access"] = 0.7

    # Industrial capacity from temporal_state (peak vs stagnant vs crisis).
    endowments["industrial_capacity"] = INDUSTRIAL_BY_STATE.get(spec.temporal_state, 0.3)

    # --- Eno fantastical endowments (Periodical System) ---
    # Sap where vegetation (fertile lowland or forest).
    if (
        "forest" in signals
        or spec.valley in ("Dawn", "Day")
        or spec.elevation is None
        or spec.elevation < 300
    ):
        endowments["sap_harvest"] = 0.5
    # Dark vs sun side of Eno (longitude) -> Rime vs Ash pilgrimage.
    if spec.longitude < 0:
        endowments["rime_collection"] = 0.4
    else:
        endowments["ash_pilgrimage"] = 0.4
    # Pitch at coastal/deep-sea sites.
    if "port" in signals or "coastal" in signals:
        endowments["pitch_depth"] = 0.5
        # Natra (salt): evaporated from the sea at the same coastal sites.
        endowments["natra_deposit"] = 0.5
    # Phos at industrial (energy) sites.
    if endowments["industrial_capacity"] > 0.4:
        endowments["phos_vent"] = 0.4
    # Element deposits for mining cities (deterministic specialization).
    if "mining_potential" in endowments:
        for element in _pick_elements(spec.name):
            endowments[f"{element}_deposit"] = 0.6
    # Rare components.
    h = _stable_hash(spec.name)
    if h % 7 == 0:
        endowments["mucus_gland"] = 0.5
    if h % 23 == 0:
        endowments["mold_deposit"] = 0.4

    return endowments


__all__ = ["INDUSTRIAL_BY_STATE", "infer_endowments"]
