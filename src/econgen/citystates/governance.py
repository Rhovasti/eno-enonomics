"""Assign governance types to citystates based on their economic/cultural data.

Uses a curated catalog of ~30 governance types (from the Eno lore taxonomy) with
matching criteria. A two-pass algorithm: hard-coded lore assignments for special
cities, then scored assignment with diversity penalty for the rest.
"""

from collections import Counter
from typing import Dict, List, Optional

from .parser import CitystateSpec


from .governance_types import (
    CATALOG,
    GovType,
    LORE_ASSIGNMENTS,
    ROOT_TO_INITIAL,
    SIMPLE_CATEGORIES,
    STATE_PATTERNS,
)


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
