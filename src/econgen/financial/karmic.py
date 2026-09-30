"""Karmic-debt SFC layer — the 7-tier offense hierarchy from the Eno lore.

Each citystate accumulates karmic debt from offenses across 7 tiers (dignity →
society), weighted 10x per tier. Intent matters (intentional > reckless > negligent
> accidental). Souls forgive most debt (generating tradeable tokens = currency);
Utaia extracts from the remaining outstanding debt.

Base unit: 1 property offense (Tier 3). 1 life offense = 100,000 dignity offenses.
"""

from typing import Dict

from pydantic import BaseModel

from ..citystates.parser import CitystateSpec
from .parameters import (
    AVG_INTENT_BY_STATE,
    DEFAULT_AVG_INTENT,
    DEFAULT_OFFENSE_RATES,
    FORGIVENESS_RATE,
    OFFENSE_RATES_BY_STATE,
    OFFENSE_TIERS,
    UTAIA_EXTRACTION_RATE,
)

FINAL_CYCLE = 998


class KarmicSFC(BaseModel):
    """Karmic-debt financial snapshot using the 7-tier offense hierarchy."""

    offenses_by_tier: Dict[str, float]  # raw offense counts per tier
    karmic_debt: float  # total weighted debt (property-offense units)
    dominant_tier: str  # tier contributing most to total debt
    forgiveness_tokens: float  # tokens generated (= forgiven debt)
    outstanding_debt: float  # unforgiven debt (Utaia-extractable)
    utai_extraction: float  # annual extraction by Utaia
    debt_to_gdp: float
    credit_standing: str  # sound / stressed / distressed


def compute_karmic_sfc(spec: CitystateSpec, gdp: float) -> KarmicSFC:
    """Compute the karmic-debt position from the offense hierarchy."""
    rates = OFFENSE_RATES_BY_STATE.get(spec.temporal_state, DEFAULT_OFFENSE_RATES)
    intent = AVG_INTENT_BY_STATE.get(spec.temporal_state, DEFAULT_AVG_INTENT)
    run_cycles = max(FINAL_CYCLE - spec.founded_cycle, 1)
    pop_factor = max(spec.population, 1) / 1000.0

    # Offense counts per tier (rate × pop × cycles × intent).
    offenses_by_tier: Dict[str, float] = {}
    for i, (tier_name, _weight) in enumerate(OFFENSE_TIERS):
        offenses_by_tier[tier_name] = rates[i] * pop_factor * run_cycles * intent

    # Weighted debt: Σ(offenses × tier_weight).
    karmic_debt = sum(offenses_by_tier[name] * weight for name, weight in OFFENSE_TIERS)

    # Dominant tier (highest weighted contribution).
    contributions = {name: offenses_by_tier[name] * weight for name, weight in OFFENSE_TIERS}
    dominant_tier = max(contributions, key=contributions.get) if contributions else "property"

    # Forgiveness: souls forgive most debt → generates tokens (currency).
    forgiveness_tokens = karmic_debt * FORGIVENESS_RATE
    outstanding_debt = karmic_debt - forgiveness_tokens

    # Utaia extracts from outstanding (unforgiven) debt.
    utai_extraction = outstanding_debt * UTAIA_EXTRACTION_RATE

    debt_to_gdp = karmic_debt / gdp if gdp > 0 else 0.0
    if debt_to_gdp > 0.50:
        credit = "distressed"
    elif debt_to_gdp > 0.20:
        credit = "stressed"
    else:
        credit = "sound"

    return KarmicSFC(
        offenses_by_tier=offenses_by_tier,
        karmic_debt=karmic_debt,
        dominant_tier=dominant_tier,
        forgiveness_tokens=forgiveness_tokens,
        outstanding_debt=outstanding_debt,
        utai_extraction=utai_extraction,
        debt_to_gdp=debt_to_gdp,
        credit_standing=credit,
    )


__all__ = ["KarmicSFC", "compute_karmic_sfc"]
