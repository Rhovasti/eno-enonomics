"""Bridge a ``CitystateSpec`` to the Enonomics static pipeline (Operator + supply/demand).

Shared by the market-price precompute and the per-city simulator. Reuses
``CapacityCalculator`` / ``DemandCalculator`` / ``RulesEngine`` and the fantastical
default taxonomy/rules/demand (see ``fantastical.py``).
"""

from decimal import Decimal
from typing import Dict, Tuple

from ..demand import DemandCalculator, create_default_demand_profiles
from ..models import Operator, TechLevel
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
        if rule.capacity_driver:
            endowment = operator.endowments.get(rule.capacity_driver, Decimal("0"))
            factor = 1.0 + float(endowment)
        else:
            factor = 1.0  # universal rules (e.g. dust)
        labor = max(float(rule.labor_required), 0.1)
        for resource, ratio in rule.outputs.items():
            production = operator.population * factor * tech * float(ratio) / labor
            supply[resource] = supply.get(resource, Decimal("0")) + Decimal(str(production))
    return supply


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


__all__ = [
    "spec_to_operator",
    "make_economy",
    "city_supply_demand",
    "supply_for_operator",
]
