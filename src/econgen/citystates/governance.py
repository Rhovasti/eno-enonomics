"""Assign governance types to citystates based on their economic/cultural data.

Uses a curated catalog of ~30 governance types (from the Eno lore taxonomy) with
matching criteria. A two-pass algorithm: hard-coded lore assignments for special
cities, then scored assignment with diversity penalty for the rest.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .parser import CitystateSpec


@dataclass
class GovType:
    name: str
    category: str
    eno_note: str
    temporal_states: Set[str] = field(default_factory=set)
    valleys: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    infrastructure: Set[str] = field(default_factory=set)
    avoid_infra: Set[str] = field(default_factory=set)
    pop_max: int = 999999
    pop_min: int = 0
    economic: str = ""  # "crisis" / "prosperous" / "trade_surplus" / "large_gdp" / ""
    state_field: Set[str] = field(default_factory=set)  # preferred state field values


# === Curated governance catalog (~30 types) ===
CATALOG: List[GovType] = [
    GovType(
        "Acephalous Society",
        "Kinship & Non-State",
        "Day Valley nomads; free people without permanent leaders.",
        temporal_states={"Drifters", "Wildlands", "Day"},
        valleys={"Day"},
        pop_max=3000,
        avoid_infra={"citadel", "walls"},
    ),
    GovType(
        "Segmentary Lineage",
        "Kinship & Non-State",
        "Highland nomads; close-knit family units that fuse against threats.",
        temporal_states={"Drifters", "Wildlands"},
        tags={"highland", "nomadic"},
        pop_max=5000,
    ),
    GovType(
        "Segmentary State (Mandala)",
        "Kinship & Non-State",
        "Large citystate with soft, fading sphere of influence.",
        state_field={"Regional Capital"},
        pop_min=10000,
    ),
    GovType(
        "Age-Grade System",
        "Kinship & Non-State",
        "Aumian subterranean tribes; responsibilities shift with age.",
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"underground", "subterranean"},
        pop_max=8000,
    ),
    GovType(
        "Heterarchy",
        "Kinship & Non-State",
        "Dawn Valley; different leaders hold power in different contexts.",
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"multicultural"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Absolute Monarchy",
        "Autocracy & Monarchy",
        "Unlimited sovereign authority in a single ruler.",
        tags={"capital", "monarchy"},
        infrastructure={"citadel", "walls"},
        state_field={"Capital"},
        temporal_states={"Dusk", "Noon"},
    ),
    GovType(
        "Constitutional Monarchy",
        "Autocracy & Monarchy",
        "Crown restricted by legal framework; progressive transition.",
        tags={"capital"},
        infrastructure={"plaza"},
        temporal_states={"Day"},
        state_field={"Capital"},
        economic="prosperous",
    ),
    GovType(
        "Diarchy",
        "Autocracy & Monarchy",
        "Two rulers from different cultural groups share governance.",
        tags={"multicultural", "bicultural"},
        infrastructure={"citadel", "plaza"},
        temporal_states={"Day", "Dusk"},
    ),
    GovType(
        "Elective Monarchy",
        "Autocracy & Monarchy",
        "Council elects the monarch from eligible noble houses.",
        valleys={"Day"},
        tags={"capital", "peak-power"},
        infrastructure={"plaza"},
        temporal_states={"Day"},
    ),
    GovType(
        "Aristocracy",
        "Oligarchy & Minority Rule",
        "Rule by hereditary landed elite.",
        infrastructure={"citadel", "walls"},
        tags={"aristocratic", "noble"},
        temporal_states={"Dusk", "Noon"},
        avoid_infra={"shanty_town"},
    ),
    GovType(
        "Plutocracy",
        "Oligarchy & Minority Rule",
        "Rule by the wealthy; the state extracts for the elite.",
        tags={"peak-power"},
        economic="large_gdp",
        state_field={"Valar Dominion of Worth"},
    ),
    GovType(
        "Stratocracy",
        "Oligarchy & Minority Rule",
        "Direct military rule; civil and military command fused.",
        tags={"military", "fortress", "citadel"},
        infrastructure={"citadel", "walls"},
        temporal_states={"Night"},
        state_field={"Capital"},
    ),
    GovType(
        "Technocracy",
        "Oligarchy & Minority Rule",
        "Rule by technical experts based on data and science.",
        tags={"industrial", "scholarly"},
        temporal_states={"Day", "Dawn"},
        economic="prosperous",
    ),
    GovType(
        "Gerontocracy",
        "Oligarchy & Minority Rule",
        "Governance by the eldest members; wisdom over innovation.",
        temporal_states={"Noon", "Dusk"},
        infrastructure={"temple"},
        tags={"stagnant", "traditional"},
    ),
    GovType(
        "Theocracy",
        "Theocracy & Ideological",
        "Clerical class governs through divine law.",
        infrastructure={"temple"},
        tags={"religious", "sacred", "temple"},
        temporal_states={"Dusk", "Night"},
    ),
    GovType(
        "Direct Democracy",
        "Democratic & Republican",
        "Citizens vote directly on laws and policies.",
        infrastructure={"plaza"},
        temporal_states={"Day"},
        pop_max=8000,
        economic="prosperous",
    ),
    GovType(
        "Sortition (Demarchy)",
        "Democratic & Republican",
        "Leaders chosen by lottery; Erno's ideal of chance governance.",
        infrastructure={"plaza"},
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"innovative"},
    ),
    GovType(
        "Consociationalism",
        "Democratic & Republican",
        "Power-sharing for deeply divided multicultural societies.",
        tags={"multicultural"},
        pop_min=5000,
        temporal_states={"Day", "Dusk"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Guild Socialism",
        "Socialist Experiment",
        "Workers run industries via autonomous guilds.",
        tags={"industrial"},
        temporal_states={"Day", "Dawn"},
        infrastructure={"plaza"},
        economic="prosperous",
    ),
    GovType(
        "Merchant City Republic",
        "Democratic & Republican",
        "Port city governed by merchant elites and trade councils.",
        infrastructure={"port"},
        tags={"commercial", "trade"},
        state_field={"Independent"},
        economic="trade_surplus",
    ),
    GovType(
        "Chiefdom",
        "Tribal & Early Agricultural",
        "Tribal sedentary society led by a chief.",
        tags={"tribal"},
        state_field={"Settlement"},
        pop_max=5000,
        temporal_states={"Drifters", "Wildlands", "Dawn"},
    ),
    GovType(
        "Council of Elders",
        "Tribal & Early Agricultural",
        "Village governed by a council of the eldest and wisest.",
        infrastructure={"temple", "plaza"},
        state_field={"Council of Zmur", "Settlement"},
        pop_max=6000,
        temporal_states={"Dusk", "Noon"},
    ),
    GovType(
        "Warrior Aristocracy",
        "Tribal & Early Agricultural",
        "Military elite rules from fortified positions.",
        tags={"military", "fortress", "warrior"},
        infrastructure={"walls", "citadel"},
        temporal_states={"Night", "Dusk"},
    ),
    GovType(
        "Kakistocracy",
        "Fringe",
        "Government by the least qualified; a failed or corrupt state.",
        temporal_states={"Night", "Symbiotic Decline"},
        tags={"crisis", "failed"},
        infrastructure={"shanty_town"},
        economic="crisis",
    ),
    GovType(
        "Ochlocracy",
        "Fringe",
        "Mob rule; the passions of the masses override law.",
        temporal_states={"Night"},
        tags={"fear-driven", "crisis"},
        pop_min=10000,
        economic="crisis",
    ),
    GovType(
        "Irrigation Bureaucracy",
        "Fringe",
        "Hydraulic despotism around a great dam.",
        valleys={"Dawn"},
        infrastructure={"river access", "farms"},
        tags={"dam", "irrigation"},
    ),
    GovType(
        "Minarchism",
        "Libertarian & Anarchist",
        "Night-watchman state; minimal governance in Dusk Valley.",
        valleys={"Dusk"},
        state_field={"Independent"},
        temporal_states={"Dusk"},
        avoid_infra={"citadel"},
    ),
    GovType(
        "Secret Society Governance",
        "Fringe",
        "Shadowy elite governs through secrets and information control.",
        infrastructure={"temple"},
        tags={"mysterious", "secret"},
        state_field={"Citadel of Almo"},
    ),
    GovType(
        "Corporate Sovereignty",
        "Libertarian & Anarchist",
        "Trade company governs territory as a corporate entity.",
        infrastructure={"port"},
        tags={"commercial", "industrial"},
        state_field={"Trade Company of Ataria", "Independent"},
    ),
    GovType(
        "Sacred Kingship",
        "Theocracy & Ideological",
        "Divine ruler combining temporal and spiritual authority.",
        infrastructure={"temple", "citadel"},
        tags={"religious", "sacred", "capital"},
        temporal_states={"Dusk"},
    ),
    GovType(
        "Charter City",
        "Libertarian & Anarchist",
        "Semi-autonomous innovation zone attracting investment.",
        infrastructure={"port"},
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"innovative", "commercial"},
        pop_max=15000,
    ),
    GovType(
        "Pirate/Outlaw Governance",
        "Fringe",
        "Floating direct-democracy of seafarers outside the law.",
        infrastructure={"port"},
        tags={"sea", "raider", "nomadic"},
        temporal_states={"Drifters", "Wildlands", "Winds"},
        pop_max=8000,
    ),
    # --- Expanded types (+15) ---
    GovType(
        "Cybernetic Socialism",
        "Socialist Experiment",
        "Economy managed in real-time by soulsphere feedback loops (Project Cybersyn style).",
        tags={"constructed", "soulsphere", "algorithmic"},
        temporal_states={"Day", "Dawn"},
        economic="prosperous",
    ),
    GovType(
        "Oriental Despotism",
        "Autocracy & Monarchy",
        "Hydraulic empire; centralized bureaucratic despotism around water infrastructure.",
        infrastructure={"river access"},
        tags={"dam", "hydraulic", "lake"},
        valleys={"Dawn"},
    ),
    GovType(
        "Personalist Dictatorship",
        "Autocracy & Monarchy",
        "Power rests on charisma or military backing, untethered to royal lineage.",
        tags={"autocrat", "dictator"},
        temporal_states={"Night"},
        infrastructure={"citadel"},
    ),
    GovType(
        "Kritarchy",
        "Oligarchy & Minority Rule",
        "Rule by judges; governance through a legal system and courts.",
        tags={"legal", "judge", "court"},
        infrastructure={"plaza"},
        temporal_states={"Dusk"},
    ),
    GovType(
        "Noocracy",
        "Oligarchy & Minority Rule",
        "Rule by philosophers and intellectuals; wisdom-based governance.",
        tags={"scholarly", "philosopher", "wise"},
        temporal_states={"Day", "Noon"},
        infrastructure={"temple"},
    ),
    GovType(
        "Anarcho-Syndicalism",
        "Socialist Experiment",
        "Stateless society organized into worker-run trade unions.",
        tags={"worker", "union", "industrial"},
        temporal_states={"Day"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Council Communism",
        "Socialist Experiment",
        "Governance through local democratic workers' councils.",
        tags={"council", "soviet", "worker"},
        temporal_states={"Day", "Dawn"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Libertarian Municipalism",
        "Socialist Experiment",
        "State dissolved into neighborhood assemblies using direct democracy.",
        infrastructure={"plaza"},
        temporal_states={"Dawn", "Day"},
        tags={"community", "assembly"},
        pop_max=10000,
    ),
    GovType(
        "Timocracy",
        "Oligarchy & Minority Rule",
        "Rule by property owners valuing honor and civic virtue.",
        tags={"property", "honor", "landowner"},
        temporal_states={"Dusk"},
        economic="prosperous",
    ),
    GovType(
        "Big-man Society",
        "Kinship & Non-State",
        "Pre-state prestige-based governance; influence through generosity.",
        tags={"tribal", "nomadic"},
        temporal_states={"Drifters", "Wildlands", "Dawn"},
        pop_max=3000,
    ),
    GovType(
        "Temple Economy",
        "Theocracy & Ideological",
        "Temple-centered redistribution; priests control production and storage.",
        infrastructure={"temple"},
        tags={"religious", "sacred", "redistribution"},
        temporal_states={"Dusk", "Noon"},
    ),
    GovType(
        "Palace Economy",
        "Autocracy & Monarchy",
        "Palace-centered redistribution; elite controls all production.",
        infrastructure={"citadel"},
        tags={"palace", "royal"},
        temporal_states={"Dusk", "Noon"},
        state_field={"Capital"},
    ),
    GovType(
        "Village Republic",
        "Democratic & Republican",
        "Small self-governing village with direct citizen participation.",
        infrastructure={"plaza"},
        temporal_states={"Day", "Dawn"},
        pop_max=4000,
        economic="prosperous",
    ),
    GovType(
        "Tribal Confederation",
        "Kinship & Non-State",
        "League of independent tribes united for mutual defense.",
        tags={"tribal", "confederation", "nomadic"},
        temporal_states={"Drifters", "Wildlands"},
        pop_min=3000,
    ),
    GovType(
        "Panarchy",
        "Libertarian & Anarchist",
        "Multiple governance types coexist; citizens choose their political provider.",
        tags={"multicultural", "diverse", "pluralist"},
        temporal_states={"Day"},
        infrastructure={"plaza"},
    ),
]

# Hard-coded lore assignments (name → type name).
LORE_ASSIGNMENTS: Dict[str, str] = {
    "Citadel of Utaia": "Plutocracy",
    "Citadel of the Pass": "Stratocracy",
    "Citadel of Almo": "Secret Society Governance",
    "Guild": "Merchant City Republic",
}

# State-field pattern → governance type.
STATE_PATTERNS = {
    "council": "Council of Elders",
    "republic": "Direct Democracy",
    "trade company": "Corporate Sovereignty",
    "principality": "Constitutional Monarchy",
    "community": "Direct Democracy",
    "dominion": "Plutocracy",
}


class GovernanceAssignment:
    """The result of assigning a governance type to a citystate."""

    def __init__(
        self,
        name: str,
        gov_type: str,
        category: str,
        eno_note: str,
        score: float,
        rationale: List[str],
        hard_coded: bool = False,
    ):
        self.name = name
        self.gov_type = gov_type
        self.category = category
        self.eno_note = eno_note
        self.score = score
        self.rationale = rationale
        self.hard_coded = hard_coded

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gov_type": self.gov_type,
            "category": self.category,
            "eno_note": self.eno_note,
            "score": round(self.score, 1),
            "rationale": self.rationale,
            "hard_coded": self.hard_coded,
        }


def _hard_code(spec: CitystateSpec, state_field: str) -> Optional[str]:
    """Check for hard-coded lore assignments by name or state field."""
    if spec.name in LORE_ASSIGNMENTS:
        return LORE_ASSIGNMENTS[spec.name]
    state_lower = state_field.lower()
    for pattern, gov_type in STATE_PATTERNS.items():
        if pattern in state_lower:
            return gov_type
    return None


def _score_type(
    spec: CitystateSpec, gov: GovType, state_field: str, economic: dict, type_counts: Counter
) -> tuple:
    """Score a governance type for a citystate. Returns (score, rationale)."""
    score = 0.0
    reasons: List[str] = []

    if spec.temporal_state in gov.temporal_states:
        score += 20
        reasons.append(f"{spec.temporal_state} state")
    if spec.valley in gov.valleys:
        score += 15
        reasons.append(f"{spec.valley} valley")

    tags_lower = {t.lower() for t in spec.tags}
    tag_matches = gov.tags & tags_lower
    if tag_matches:
        score += min(len(tag_matches) * 10, 30)
        reasons.append(f"tags: {', '.join(sorted(tag_matches)[:2])}")

    infra_lower = {i.lower() for i in spec.infrastructure}
    infra_matches = gov.infrastructure & infra_lower
    if infra_matches:
        score += min(len(infra_matches) * 10, 20)
        reasons.append(f"infrastructure: {', '.join(sorted(infra_matches)[:2])}")

    if gov.avoid_infra & infra_lower:
        score -= 15
        reasons.append(f"avoid: {', '.join(sorted(gov.avoid_infra & infra_lower)[:1])}")

    if spec.population > gov.pop_max:
        score -= 15
    elif spec.population < gov.pop_min:
        score -= 10
    else:
        score += 10
        reasons.append(f"pop {spec.population:,}")

    if state_field in gov.state_field:
        score += 15
        reasons.append(f"state: {state_field}")

    # Economic fit.
    if gov.economic == "crisis" and economic.get("financial_health") in ("crisis", "vulnerable"):
        score += 15
        reasons.append("economic crisis")
    elif gov.economic == "prosperous" and economic.get("financial_health") in (
        "prosperous",
        "stable",
    ):
        score += 15
        reasons.append("economic stability")
    elif gov.economic == "trade_surplus" and economic.get("trade_balance", 0) < 0:
        score += 10
        reasons.append("trade surplus")
    elif gov.economic == "large_gdp" and economic.get("gdp", 0) > 50000:
        score += 10
        reasons.append("high GDP")

    # Diversity penalty.
    count = type_counts.get(gov.name, 0)
    if count >= 8:
        score -= (count - 7) * 10

    return score, reasons[:3]


def assign_governance(
    specs: List[CitystateSpec],
    economic_data: Optional[Dict[str, dict]] = None,
) -> List[GovernanceAssignment]:
    """Assign governance types to all citystates with diversity."""
    economic_data = economic_data or {}
    assignments: List[GovernanceAssignment] = []
    type_counts: Counter = Counter()

    for spec in specs:
        state_field = spec.state
        econ = economic_data.get(spec.name, {})

        # Pass 1: hard-coded.
        hard = _hard_code(spec, state_field)
        if hard:
            gov = next((g for g in CATALOG if g.name == hard), None)
            if gov:
                assignment = GovernanceAssignment(
                    spec.name,
                    gov.name,
                    gov.category,
                    gov.eno_note,
                    100.0,
                    ["hard-coded lore assignment"],
                    hard_coded=True,
                )
                assignments.append(assignment)
                type_counts[gov.name] += 1
                continue

        # Pass 2: scored.
        best_score = -999.0
        best_gov: Optional[GovType] = None
        best_reasons: List[str] = []
        for gov in CATALOG:
            score, reasons = _score_type(spec, gov, state_field, econ, type_counts)
            if score > best_score:
                best_score = score
                best_gov = gov
                best_reasons = reasons

        if best_gov:
            assignments.append(
                GovernanceAssignment(
                    spec.name,
                    best_gov.name,
                    best_gov.category,
                    best_gov.eno_note,
                    best_score,
                    best_reasons,
                )
            )
            type_counts[best_gov.name] += 1

    return assignments


__all__ = [
    "GovernanceAssignment",
    "assign_governance",
    "assign_initial_governance",
    "compute_progression",
    "create_dam_settlement",
    "CATALOG",
    "LORE_ASSIGNMENTS",
    "ROOT_TO_INITIAL",
]


# Root → preferred initial governance types (for founding-era assignment).
ROOT_TO_INITIAL: Dict[str, List[str]] = {
    "Fortified Settlement": ["Chiefdom", "Warrior Aristocracy", "Absolute Monarchy"],
    "Trade Outpost": ["Big-man Society", "Merchant City Republic", "Acephalous Society"],
    "Fishing Village": ["Acephalous Society", "Village Republic", "Council of Elders"],
    "Agricultural Settlement": ["Council of Elders", "Chiefdom", "Heterarchy"],
    "Mining Camp": ["Big-man Society", "Stratocracy", "Chiefdom"],
    "Religious Sanctuary": ["Sacred Kingship", "Theocracy", "Council of Elders"],
    "Refuge Colony": ["Acephalous Society", "Consociationalism", "Segmentary Lineage"],
    "Nomadic Camp": ["Segmentary Lineage", "Tribal Confederation", "Acephalous Society"],
    "Political Experiment": ["Sortition (Demarchy)", "Heterarchy", "Direct Democracy"],
    "Administrative Center": ["Chiefdom", "Palace Economy", "Absolute Monarchy"],
    "Craft Settlement": ["Guild Socialism", "Heterarchy", "Council of Elders"],
    "Outlaw Haven": ["Pirate/Outlaw Governance", "Kakistocracy", "Acephalous Society"],
    "Hydraulic Settlement": ["Oriental Despotism", "Palace Economy", "Chiefdom"],
}

# Types considered "simple" (suitable for founding-era initial governance).
SIMPLE_CATEGORIES = {"Kinship & Non-State", "Tribal & Early Agricultural"}
SIMPLE_TYPES = {g.name for g in CATALOG if g.category in SIMPLE_CATEGORIES}
# Advanced types that are almost never initial (emerge through progression).
ADVANCED_TYPES = {
    "Cybernetic Socialism",
    "Technocracy",
    "Noocracy",
    "Kritarchy",
    "Anarcho-Syndicalism",
    "Council Communism",
    "Libertarian Municipalism",
    "Panarchy",
    "Timocracy",
    "Corporate Sovereignty",
}


def assign_initial_governance(
    specs: List[CitystateSpec],
    roots: Dict[str, str],
    settled: Dict[str, str],
) -> Dict[str, str]:
    """Assign initial governance (at founding) for each citystate.

    Uses the Root type to prefer simpler governance types, with a coverage
    constraint ensuring all ~45 types appear at least once.
    """
    from .roots import assign_root  # noqa: F401 (already used externally)

    gov_by_name = {g.name: g for g in CATALOG}
    initial: Dict[str, str] = {}
    type_counts: Counter = Counter()

    # Pass 1: assign based on Root preferences + scoring.
    for spec in specs:
        root = roots.get(spec.name, "Agricultural Settlement")
        preferred = ROOT_TO_INITIAL.get(root, ["Chiefdom"])

        # Score preferred types; pick the best that differs from settled.
        settled_type = settled.get(spec.name, "")
        best_score = -999.0
        best_type = preferred[0]  # fallback
        for pname in preferred:
            if pname not in gov_by_name:
                continue
            gov = gov_by_name[pname]
            score, _ = _score_type(spec, gov, spec.state, {}, type_counts)
            # Boost: Root-preferred types get +30.
            score += 30
            # Penalty: same as settled (prefer progression).
            if pname == settled_type:
                score -= 15
            # Diversity penalty.
            count = type_counts.get(pname, 0)
            if count >= 5:
                score -= (count - 4) * 10
            if score > best_score:
                best_score = score
                best_type = pname

        initial[spec.name] = best_type
        type_counts[best_type] += 1

    # Pass 2: coverage — ensure all types appear at least once.
    assigned_types = set(initial.values())
    unassigned = [g.name for g in CATALOG if g.name not in assigned_types]

    for missing_type in unassigned:
        # Find the citystate where this type scores best as an override.
        best_city = None
        best_gain = -999.0
        for spec in specs:
            current = initial[spec.name]
            gov = gov_by_name[missing_type]
            score, _ = _score_type(spec, gov, spec.state, {}, Counter())
            current_gov = gov_by_name[current]
            current_score, _ = _score_type(spec, current_gov, spec.state, {}, Counter())
            gain = score - current_score
            # Don't override hard-coded or special assignments.
            if spec.name in LORE_ASSIGNMENTS:
                continue
            if gain > best_gain:
                best_gain = gain
                best_city = spec.name
        if best_city:
            initial[best_city] = missing_type

    return initial


def compute_progression(initial: str, settled: str) -> str:
    """Label the political trajectory from initial → settled governance."""
    if initial == settled:
        return "continuity"

    initial_gov = next((g for g in CATALOG if g.name == initial), None)
    settled_gov = next((g for g in CATALOG if g.name == settled), None)
    if not initial_gov or not settled_gov:
        return "transition"

    i_cat = initial_gov.category
    s_cat = settled_gov.category

    # Collapse → kakistocracy/ochlocracy.
    if settled in ("Kakistocracy", "Ochlocracy"):
        return "collapse"
    # Democracy → autocracy.
    democratic = {"Democratic & Republican", "Socialist Experiment"}
    autocratic = {"Autocracy & Monarchy", "Totalitarian & Fascist"}
    if i_cat in democratic and s_cat in autocratic:
        return "coup"
    # Autocracy → democracy.
    if i_cat in autocratic and s_cat in democratic:
        return "revolution"
    # Monarchy reform.
    if initial == "Absolute Monarchy" and settled == "Constitutional Monarchy":
        return "reform"
    # Simple → complex (maturation).
    if i_cat in SIMPLE_CATEGORIES and s_cat not in SIMPLE_CATEGORIES:
        return "maturation"
    # Default.
    return "evolution"


def create_dam_settlement() -> CitystateSpec:
    """Create a synthetic CitystateSpec for the dam settlement (Oriental Despotism)."""
    return CitystateSpec(
        name="Valvestrum",
        founded_cycle=50,
        population=3500,
        growth_rate=0.015,
        temporal_state="Dawn",
        valley="Dawn",
        latitude=45.0,
        longitude=30.0,
        elevation=850,
        infrastructure=["citadel", "river access", "farms"],
        tags=["location", "city", "dawn-valley", "hydraulic", "dam", "lake", "industrial"],
        state="Hydraulic Dominion",
        source_file="synthetic",
    )
