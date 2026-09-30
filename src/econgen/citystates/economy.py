"""Bridge a ``CitystateSpec`` to the Enonomics static pipeline (Operator + supply/demand).

Shared by the market-price precompute and the per-city simulator. Reuses
``CapacityCalculator`` / ``DemandCalculator`` / ``RulesEngine`` and the fantastical
default taxonomy/rules/demand (see ``fantastical.py``).
"""

from decimal import Decimal
from typing import Dict, Tuple

from ..demand import DemandCalculator, create_default_demand_profiles
from ..models import TECH_ORDER, Operator, ProductionRule, TechLevel
from ..rules import RulesEngine, create_default_rules
from ..taxonomy import ResourceTaxonomy, create_default_taxonomy
from .endowments import infer_endowments
from .parser import CitystateSpec

# Population-linear tech factor (citystates use real populations ~thousands, so
# production must scale ~linearly with population to match demand ∝ population;
# the multi-city CapacityCalculator's sqrt(pop)/10000 was tuned for the bogus 30M
# geojson and under-produces here by ~1000x).
_TECH_FACTOR = {"tribal": 0.5, "medieval": 1.0, "industrial": 1.5}


def _tech_for(spec: CitystateSpec) -> str:
    """Derive a static tech tier from tags + temporal_state (Phase 2; Phase 3 evolves it)."""
    tags_l = {t.lower() for t in spec.tags}
    if "industrial" in tags_l:
        return "industrial"
    if spec.temporal_state in (
        "Drifters",
        "Wildlands",
        "Winds",
        "Dwellers",
        "Night",
        "Symbiotic Decline",
    ):
        return "tribal"
    return "medieval"


def spec_to_operator(spec: CitystateSpec) -> Operator:
    """Build an ``Operator`` (with inferred endowments) from a citystate spec."""
    # Clamp coords to the valid WGS84 range (a few source profiles have typos like
    # latitude 93.47; endowment inference uses longitude/elevation, not latitude).
    lat = max(-89.9, min(89.9, spec.latitude))
    lon = max(-179.9, min(179.9, spec.longitude))
    return Operator(
        operator_id=spec.name,
        name=spec.name,
        kind="city",
        tech=TechLevel(_tech_for(spec)),
        coord=(lat, lon),
        population=spec.population,
        tags=list(spec.tags),
        endowments={k: Decimal(str(v)) for k, v in infer_endowments(spec).items()},
    )


def make_economy() -> Tuple[ResourceTaxonomy, RulesEngine, DemandCalculator]:
    """Build the default (fantastical-enabled) taxonomy/rules/demand calculators."""
    taxonomy = create_default_taxonomy()
    rules_engine = RulesEngine(create_default_rules())
    demand_calc = DemandCalculator(taxonomy, create_default_demand_profiles())
    return taxonomy, rules_engine, demand_calc


def supply_for_operator(operator: Operator, rules_engine: RulesEngine) -> Dict[str, Decimal]:
    """Population-linear supply: production ∝ population × endowment × tech / labor.

    Scales with population (like demand) so cities can be self-sufficient or
    surplus/deficit — unlike the multi-city sqrt(pop)/10000 capacity formula.
    """
    tech = _TECH_FACTOR.get(str(operator.tech), 1.0)
    supply: Dict[str, Decimal] = {}
    for rule in rules_engine.get_eligible_rules(operator):
        for resource, production in _rule_output(operator, rule, tech).items():
            supply[resource] = supply.get(resource, Decimal("0")) + production
    return supply


def potential_supply_for_operator(
    operator: Operator, rules_engine: RulesEngine
) -> Tuple[Dict[str, Decimal], Dict[str, int]]:
    """Current supply plus resources the city unlocks as its tech level rises.

    The dynamic simulator gates production on a rising tech level, which can only
    switch on resources that have a production rate. Resources already produced
    keep their current rates; each resource first reachable at a higher tier (given
    the city's endowments) is added at that tier's tech factor.

    Args:
        operator: The citystate operator at its founding tech level
        rules_engine: Production rules

    Returns:
        Tuple of (supply, unlock_rank), where unlock_rank maps each added resource
        to the tech rank (``TECH_ORDER``) at which the city can first produce it
    """
    supply = supply_for_operator(operator, rules_engine)
    unlock_rank: Dict[str, int] = {}
    current_rank = TECH_ORDER[str(operator.tech)]
    for level, rank in sorted(TECH_ORDER.items(), key=lambda item: item[1]):
        if rank <= current_rank:
            continue
        upgraded = operator.model_copy(update={"tech": TechLevel(level)})
        tier_supply = supply_for_operator(upgraded, rules_engine)
        for resource, production in tier_supply.items():
            if resource not in supply:
                supply[resource] = production
                unlock_rank[resource] = rank
    return supply, unlock_rank


def _rule_output(operator: Operator, rule: ProductionRule, tech: float) -> Dict[str, Decimal]:
    """Output of one rule for an operator at the given tech factor."""
    if rule.capacity_driver:
        endowment = operator.endowments.get(rule.capacity_driver, Decimal("0"))
        factor = 1.0 + float(endowment)
    else:
        factor = 1.0  # universal rules (e.g. dust)
    labor = max(float(rule.labor_required), 0.1)
    return {
        resource: Decimal(str(operator.population * factor * tech * float(ratio) / labor))
        for resource, ratio in rule.outputs.items()
    }


def city_supply_demand(
    spec: CitystateSpec,
    taxonomy: ResourceTaxonomy,
    rules_engine: RulesEngine,
    demand_calc: DemandCalculator,
) -> Tuple[Dict[str, Decimal], Dict[str, Decimal]]:
    """Return (supply, demand) dicts {resource_id: qty} for one citystate."""
    operator = spec_to_operator(spec)
    supply = supply_for_operator(operator, rules_engine)
    demand_all = demand_calc.calculate_all_demand([operator])
    demand = demand_all.get(operator.operator_id, {})
    return supply, demand


def city_potential_supply_demand(
    spec: CitystateSpec,
    taxonomy: ResourceTaxonomy,
    rules_engine: RulesEngine,
    demand_calc: DemandCalculator,
) -> Tuple[Dict[str, Decimal], Dict[str, Decimal], Dict[str, int]]:
    """Return (potential supply, demand, unlock_rank) for the dynamic simulator.

    See ``potential_supply_for_operator``: supply includes resources the city only
    reaches at a higher tech tier, with the rank at which each unlocks.
    """
    operator = spec_to_operator(spec)
    supply, unlock_rank = potential_supply_for_operator(operator, rules_engine)
    demand = demand_calc.calculate_all_demand([operator]).get(operator.operator_id, {})
    return supply, demand, unlock_rank


__all__ = [
    "spec_to_operator",
    "make_economy",
    "city_supply_demand",
    "city_potential_supply_demand",
    "supply_for_operator",
    "potential_supply_for_operator",
]
