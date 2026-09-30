"""Precompute the world market price per resource (Phase A of market price-taker).

Runs the static pipeline on all citystates at once and takes, per resource, the
mean of the role-based scarcity prices across cities — a single representative
"world" price each city trades against. Phase 2 holds it constant (the economy is
steady-state); Phase 3 can make it a time series.
"""

from collections import defaultdict
from typing import Dict, List

from ..models import SimulationConfig
from ..pricing import PriceCalculator
from ..rules import RulesEngine
from ..taxonomy import ResourceTaxonomy
from .economy import DemandCalculator, spec_to_operator, supply_for_operator
from .parser import CitystateSpec


def compute_market_prices(
    specs: List[CitystateSpec],
    taxonomy: ResourceTaxonomy,
    rules_engine: RulesEngine,
    demand_calc: DemandCalculator,
) -> Dict[str, float]:
    """Return ``{resource_id: world_market_price}`` averaged across all citystates."""
    operators = [spec_to_operator(spec) for spec in specs]
    supply = {op.operator_id: supply_for_operator(op, rules_engine) for op in operators}
    demand = demand_calc.calculate_all_demand(operators)

    price_calc = PriceCalculator(taxonomy, SimulationConfig())
    prices = price_calc.calculate_prices(operators, supply, demand)

    sums: Dict[str, float] = defaultdict(float)
    counts: Dict[str, int] = defaultdict(int)
    for op_prices in prices.values():
        for resource, price in op_prices.items():
            sums[resource] += float(price)
            counts[resource] += 1
    return {resource: sums[resource] / counts[resource] for resource in sums}


__all__ = ["compute_market_prices"]
