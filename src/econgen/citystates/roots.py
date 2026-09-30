"""Roots: founding-origin classification for citystates.

Each citystate started as something — a fortified outpost, a fishing village, a
mining camp. This module assigns a Root type based on the citystate's
infrastructure, tags, temporal_state, and economic signals, reflecting what the
settlement was at its founding.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .parser import CitystateSpec


@dataclass
class RootType:
    name: str
    description: str
    infrastructure: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    temporal_states: Set[str] = field(default_factory=set)
    state_field: Set[str] = field(default_factory=set)
    economic: str = ""  # "mining" / "fishing" / "craft" / ""


ROOTS: List[RootType] = [
    RootType(
        "Fortified Settlement",
        "Strategic defense outpost",
        infrastructure={"citadel", "walls"},
        tags={"fortress", "military", "strategic"},
    ),
    RootType(
        "Trade Outpost",
        "Commercial trading post",
        infrastructure={"port"},
        tags={"commercial", "trade", "market"},
    ),
    RootType(
        "Fishing Village",
        "Coastal or river fishing community",
        infrastructure={"port"},
        tags={"coastal", "sea", "fish"},
        economic="fishing",
    ),
    RootType(
        "Agricultural Settlement",
        "Farming community",
        infrastructure={"farms"},
        tags={"agricultural", "lowland", "fertile"},
        economic="agriculture",
    ),
    RootType(
        "Mining Camp",
        "Resource extraction settlement",
        tags={"mining", "mountain", "highland"},
        economic="mining",
    ),
    RootType(
        "Religious Sanctuary",
        "Temple or monastery foundation",
        infrastructure={"temple"},
        tags={"religious", "sacred", "monastery"},
    ),
    RootType(
        "Refuge Colony",
        "Settlement of displaced peoples",
        temporal_states={"Night", "Symbiotic Decline"},
        tags={"refuge", "exile"},
    ),
    RootType(
        "Nomadic Camp",
        "Settled from nomadic roots",
        temporal_states={"Drifters", "Wildlands", "Winds"},
        tags={"nomadic", "tribal"},
    ),
    RootType(
        "Political Experiment",
        "Founded with a governance vision",
        temporal_states={"Dawn"},
        tags={"innovative", "experimental", "project"},
    ),
    RootType(
        "Administrative Center",
        "Governance and administrative hub",
        state_field={"Capital", "Regional Capital"},
        tags={"capital"},
    ),
    RootType(
        "Craft Settlement",
        "Artisanal production center",
        infrastructure={"plaza"},
        tags={"craft", "artisan", "industrial"},
        economic="craft",
    ),
    RootType(
        "Outlaw Haven",
        "Founded by outcasts and rogues",
        tags={"raider", "outlaw", "pirate", "thieves"},
    ),
    RootType(
        "Hydraulic Settlement",
        "Founded around water infrastructure",
        infrastructure={"river access"},
        tags={"dam", "hydraulic", "irrigation", "lake"},
    ),
]


def assign_root(spec: CitystateSpec) -> str:
    """Assign the best-fitting Root type to a citystate."""
    infra_lower = {i.lower() for i in spec.infrastructure}
    tags_lower = {t.lower() for t in spec.tags}

    best_score = -1
    best_root = "Agricultural Settlement"  # default

    for root in ROOTS:
        score = 0
        if root.infrastructure & infra_lower:
            score += len(root.infrastructure & infra_lower) * 15
        if root.tags & tags_lower:
            score += len(root.tags & tags_lower) * 10
        if spec.temporal_state in root.temporal_states:
            score += 15
        if spec.state in root.state_field:
            score += 20
        # Economic signals via endowment hints in tags
        if root.economic == "mining" and any(
            t in tags_lower for t in ("mountain", "highland", "mine")
        ):
            score += 15
        if root.economic == "fishing" and ("port" in infra_lower or "coastal" in tags_lower):
            score += 10
        if root.economic == "agriculture" and (
            "farms" in infra_lower or spec.elevation is not None and spec.elevation < 200
        ):
            score += 10

        if score > best_score:
            best_score = score
            best_root = root.name

    return best_root


def assign_roots(specs: List[CitystateSpec]) -> Dict[str, str]:
    """Assign Roots to all citystates. Returns {name: root_type}."""
    return {spec.name: assign_root(spec) for spec in specs}


__all__ = ["ROOTS", "RootType", "assign_root", "assign_roots"]
