"""Material SFC model: value-unit GDP, income by labor tier, consumption, savings, wealth.

Reads the real economy (production × market_price = GDP; trade balance; population)
and computes the material financial flows using the Eno lore's labor-tier system
and temporal_state-derived behavioral parameters.
"""

from typing import Dict

from pydantic import BaseModel

from ..citystates.parser import CitystateSpec
from .parameters import (
    DEFAULT_PARAMS,
    FINANCIAL_PARAMS,
    LABOR_TIERS,
    TIER_DISTRIBUTION,
)


class MaterialSFC(BaseModel):
    """Material financial snapshot for one citystate (steady-state, in value units)."""

    gdp: float
    trade_balance: float
    wages: float
    consumption: float
    savings: float
    household_wealth: float
    producer_surplus: float
    income_by_tier: Dict[str, float]
    per_capita_income: float
    per_capita_wealth: float


def _params_for(state: str) -> dict:
    return FINANCIAL_PARAMS.get(state, DEFAULT_PARAMS)


def compute_material_sfc(
    spec: CitystateSpec,
    supply: Dict,
    demand: Dict,
    market_prices: Dict[str, float],
    tech: str = "medieval",
) -> MaterialSFC:
    """Compute the material financial snapshot from the real economy."""
    params = _params_for(spec.temporal_state)
    all_resources = set(supply) | set(demand)

    # GDP = production valued at market prices.
    gdp = sum(float(supply.get(r, 0)) * market_prices.get(r, 1.0) for r in all_resources)

    # Trade balance = (consumption - production) valued at market prices (+ = net import).
    trade_balance = sum(
        (float(demand.get(r, 0)) - float(supply.get(r, 0))) * market_prices.get(r, 1.0)
        for r in all_resources
    )

    # Income distribution.
    wages = params["wage_share"] * gdp
    consumption = params["propensity"] * wages
    savings = wages - consumption
    producer_surplus = gdp - wages

    # Household wealth: accumulated savings over the city's lifespan (discounted —
    # not all savings persist; wealth depreciates / is consumed over centuries).
    lifespan = max(998 - spec.founded_cycle, 1)
    household_wealth = (
        savings * min(lifespan, 300) * 0.1
    )  # cap at ~300 cycles of savings, 10% retained.

    # Income by labor tier.
    tier_dist = TIER_DISTRIBUTION.get(tech, TIER_DISTRIBUTION["medieval"])
    multipliers = [t[1] for t in LABOR_TIERS]
    total_weighted = sum(f * m for f, m in zip(tier_dist, multipliers)) or 1.0
    base_unit = wages / total_weighted if wages > 0 else 0.0
    income_by_tier: Dict[str, float] = {}
    for i, (name, mult) in enumerate(LABOR_TIERS):
        income_by_tier[name] = base_unit * mult * tier_dist[i]

    pop = max(spec.population, 1)
    return MaterialSFC(
        gdp=gdp,
        trade_balance=trade_balance,
        wages=wages,
        consumption=consumption,
        savings=savings,
        household_wealth=household_wealth,
        producer_surplus=producer_surplus,
        income_by_tier=income_by_tier,
        per_capita_income=wages / pop,
        per_capita_wealth=household_wealth / pop,
    )


__all__ = ["MaterialSFC", "compute_material_sfc"]
