"""Precompute the world market price per resource (Phase A of market price-taker).

Runs the static pipeline on all citystates at once and takes, per resource, the
mean of the scarcity prices across cities — a single representative "world"
price each city trades against. Crafted resources then get an input-cost floor
(so a stuff's price responds to the scarcity of its components: endogenous,
input-aware pricing). Phase 2 holds prices constant (the economy is
steady-state); Phase 3 can make them a time series.
"""

from collections import defaultdict

from ..dynamics.adapter import recipe_input_rates
from ..models import SimulationConfig
from ..pricing import PriceCalculator
from ..rules import RulesEngine
from ..taxonomy import ResourceTaxonomy
from .economy import DemandCalculator, spec_to_operator, supply_for_operator
from .parser import CitystateSpec

# Guild markup over input cost for the crafted-resource price floor.
ALCHEMICAL_MARGIN = 0.25


def compute_market_prices(
    specs: list[CitystateSpec],
    taxonomy: ResourceTaxonomy,
    rules_engine: RulesEngine,
    demand_calc: DemandCalculator,
) -> dict[str, float]:
    """Return ``{resource_id: world_market_price}`` averaged across all citystates."""
    operators = [spec_to_operator(spec) for spec in specs]
    supply = {op.operator_id: supply_for_operator(op, rules_engine) for op in operators}
    demand = demand_calc.calculate_all_demand(operators)

    price_calc = PriceCalculator(taxonomy, SimulationConfig())
    prices = price_calc.calculate_prices(operators, supply, demand)

    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for op_prices in prices.values():
        for resource, price in op_prices.items():
            sums[resource] += float(price)
            counts[resource] += 1
    scarcity_prices = {resource: sums[resource] / counts[resource] for resource in sums}

    return _apply_input_floors(scarcity_prices, recipe_input_rates(rules_engine))


def _apply_input_floors(
    prices: dict[str, float],
    requirements: dict[str, dict[str, float]],
    margin: float = ALCHEMICAL_MARGIN,
) -> dict[str, float]:
    """Raise crafted prices to ``(1 + margin) * sum(input_price * qty)`` when lower.

    Inputs are worth at least their recipe cost plus a guild markup, so scarcity
    of a component propagates into everything crafted from it. Because floors
    only ever take the maximum, iterating to a fixed point is order-independent
    and deterministic (the curated catalog settles in two passes; chains like
    wood -> tools -> steel -> machinery may take a few more). A resource whose
    inputs are not all priced (never traded anywhere) keeps its scarcity price.
    """
    result = dict(prices)
    for _ in range(len(requirements) + 1):
        changed = False
        for resource in sorted(result):
            rates = requirements.get(resource)
            if not rates or not all(input_id in result for input_id in rates):
                continue
            floor = (1.0 + margin) * sum(result[input_id] * qty for input_id, qty in rates.items())
            if floor > result[resource]:
                result[resource] = floor
                changed = True
        if not changed:
            break
    return result


__all__ = ["compute_market_prices"]
