"""Calibrate production capacities so world supply matches world demand."""

import logging
from decimal import Decimal
from typing import Dict, List

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
