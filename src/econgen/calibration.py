"""Calibrate production capacities so world supply matches world demand."""

import logging
from decimal import Decimal
from typing import Dict, List, Tuple

from .models import Capacity
from .rules import RulesEngine

logger = logging.getLogger(__name__)


def calibrate_capacities(
    capacities: List[Capacity],
    rules_engine: RulesEngine,
    demand: Dict[str, Dict[str, Decimal]],
    supply_demand_ratio: Decimal = Decimal("1.0"),
) -> List[Capacity]:
    """
    Scale capacities so each rule's world output equals world demand times a ratio.

    Raw capacities only fix the relative productivity of operators (population,
    endowments, tech, infrastructure). This sets the absolute scale per rule, so that
    local differences turn into surpluses and deficits that trade can balance.
    Each rule is scaled by its primary (first) output. Rules whose primary output has
    no demand anywhere are left unscaled.

    Args:
        capacities: Raw capacities from CapacityCalculator
        rules_engine: Rules engine used to look up rule outputs
        demand: Demand by operator and resource
        supply_demand_ratio: Target world supply / world demand for each resource

    Returns:
        New list of capacities with calibrated max_rate values
    """
    world_demand = _world_totals(demand)
    raw_output: Dict[str, Decimal] = {}
    for capacity in capacities:
        resource_id, ratio = _primary_output(rules_engine, capacity.rule_id)
        produced = capacity.max_rate * capacity.efficiency * ratio
        raw_output[capacity.rule_id] = (
            raw_output.get(capacity.rule_id, Decimal("0")) + produced
        )

    factors: Dict[str, Decimal] = {}
    for rule_id, produced in raw_output.items():
        resource_id, _ = _primary_output(rules_engine, rule_id)
        target = world_demand.get(resource_id, Decimal("0")) * supply_demand_ratio
        factors[rule_id] = (
            target / produced if target > 0 and produced > 0 else Decimal("1")
        )
        logger.debug(
            f"Calibration factor for {rule_id} ({resource_id}): {factors[rule_id]}"
        )

    return [
        capacity.model_copy(
            update={"max_rate": capacity.max_rate * factors[capacity.rule_id]}
        )
        for capacity in capacities
    ]


def calibrate_with_input_demand(
    capacities: List[Capacity],
    rules_engine: RulesEngine,
    final_demand: Dict[str, Dict[str, Decimal]],
    supply_demand_ratio: Decimal = Decimal("1.0"),
) -> Tuple[List[Capacity], Dict[str, Dict[str, Decimal]]]:
    """
    Calibrate capacities against final demand plus the inputs production consumes.

    Input demand depends on how much downstream goods are produced, which in turn
    depends on calibration, so calibration is repeated until total demand stops
    changing. The rule graph is acyclic, so each pass settles one more level of the
    production chain and the loop ends after at most one pass per rule.

    Args:
        capacities: Raw capacities from CapacityCalculator
        rules_engine: Rules engine used to look up rule inputs and outputs
        final_demand: Consumer demand by operator and resource
        supply_demand_ratio: Target world supply / world demand for each resource

    Returns:
        Tuple of (calibrated capacities, total demand = final + input demand)
    """
    total_demand = final_demand
    for _ in range(len(rules_engine.rules) + 1):
        calibrated = calibrate_capacities(
            capacities, rules_engine, total_demand, supply_demand_ratio
        )
        next_total = _merge_add(
            final_demand, calculate_input_demand(calibrated, rules_engine)
        )
        if next_total == total_demand:
            break
        total_demand = next_total
    return calibrated, total_demand


def calculate_input_demand(
    capacities: List[Capacity], rules_engine: RulesEngine
) -> Dict[str, Dict[str, Decimal]]:
    """
    Calculate the inputs each operator consumes to run its production at capacity.

    Args:
        capacities: Production capacities
        rules_engine: Rules engine used to look up rule inputs

    Returns:
        Input demand by operator and resource
    """
    input_demand: Dict[str, Dict[str, Decimal]] = {}
    for capacity in capacities:
        rule = rules_engine.get_rule(capacity.rule_id)
        production = capacity.max_rate * capacity.efficiency
        operator_demand = input_demand.setdefault(capacity.operator_id, {})
        for resource_id, quantity in rule.inputs.items():
            operator_demand[resource_id] = (
                operator_demand.get(resource_id, Decimal("0")) + production * quantity
            )
    return {op: resources for op, resources in input_demand.items() if resources}


def _merge_add(
    first: Dict[str, Dict[str, Decimal]], second: Dict[str, Dict[str, Decimal]]
) -> Dict[str, Dict[str, Decimal]]:
    """Add two nested operator -> resource -> quantity maps into a new map."""
    merged = {op: dict(resources) for op, resources in first.items()}
    for operator_id, resources in second.items():
        target = merged.setdefault(operator_id, {})
        for resource_id, quantity in resources.items():
            target[resource_id] = target.get(resource_id, Decimal("0")) + quantity
    return merged


def _primary_output(rules_engine: RulesEngine, rule_id: str) -> tuple[str, Decimal]:
    """Return the (resource_id, quantity) of a rule's first output."""
    rule = rules_engine.get_rule(rule_id)
    resource_id, ratio = next(iter(rule.outputs.items()))
    return resource_id, ratio


def _world_totals(quantities: Dict[str, Dict[str, Decimal]]) -> Dict[str, Decimal]:
    """Sum per-operator quantities into world totals per resource."""
    totals: Dict[str, Decimal] = {}
    for operator_quantities in quantities.values():
        for resource_id, quantity in operator_quantities.items():
            totals[resource_id] = totals.get(resource_id, Decimal("0")) + quantity
    return totals
