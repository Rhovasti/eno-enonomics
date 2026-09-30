"""The Periodical System of Eno — fantastical resources, rules, and demand.

Lore source: ``w Periodical system of Eno.md``. This module is the single source
of truth for the Eno alchemical economy layer; ``create_default_taxonomy`` /
``create_default_rules`` / ``create_default_demand_profiles`` and
``config/econ.yaml`` all draw from it.

Three tiers of fantastical material:
- **Alchemical components** (8): Dust, Mold, Mucus, Rime, Phos, Pitch, Sap, Ash —
  soul/matter primitives gathered from mythic-geography endowments.
- **Periodic elements** (9, curated from 20): Cunu(Cu), Feron(Fe), Aru(Au),
  Sira(Ag), Charon(C), Sirael(Si), Plon(Pb), Suhra(S), Natra(Na) — mined.
- **Alchemical stuffs** (9): Living Bronze, Soulstone, Dreamfire, Grave Lead,
  Wardsilver, Shapeiron, Sungold, Dustglass, Preserver's Salt — each crafted from
  an element + a component, following the lore's crafter affinities, so every
  component and element feeds at least one recipe.
"""

from decimal import Decimal

from .models import DemandProfile, ProductionRule, Resource

# (resource_id, name, tier, tech_min, base_price, perishable)
_COMPONENTS: list[tuple] = [
    ("dust", "Dust", 0, "tribal", 0.5, False),
    ("sap", "Sap", 0, "tribal", 4.0, False),
    ("phos", "Phos", 0, "medieval", 15.0, False),
    ("pitch", "Pitch", 0, "medieval", 18.0, False),
    ("ash", "Ash", 0, "medieval", 12.0, False),
    ("rime", "Rime", 0, "medieval", 20.0, False),
    ("mucus", "Mucus", 0, "medieval", 25.0, False),
    ("mold", "Mold", 0, "medieval", 30.0, False),
]

_ELEMENTS: list[tuple] = [
    ("sirael", "Sirael (Silica)", 0, "medieval", 3.0, False),
    ("plon", "Plon (Lead)", 0, "medieval", 3.0, False),
    ("suhra", "Suhra (Sulfur)", 0, "medieval", 4.0, False),
    ("cunu", "Cunu (Copper)", 0, "medieval", 4.0, False),
    ("feron", "Feron (Iron)", 0, "medieval", 5.0, False),
    ("charon", "Charon (Carbon)", 0, "medieval", 6.0, False),
    ("sira", "Sira (Silver)", 0, "medieval", 25.0, False),
    ("aru", "Aru (Gold)", 0, "medieval", 40.0, False),
    ("natra", "Natra (Salt)", 0, "medieval", 2.0, False),
]

_STUFFS: list[tuple] = [
    ("grave-lead", "Grave Lead", 2, "medieval", 35.0, False),
    ("dreamfire", "Dreamfire", 2, "medieval", 50.0, False),
    ("living-bronze", "Living Bronze", 2, "medieval", 45.0, False),
    ("soulstone", "Soulstone", 2, "medieval", 60.0, False),
    ("wardsilver", "Wardsilver", 2, "medieval", 55.0, False),
    ("shapeiron", "Shapeiron", 2, "medieval", 40.0, False),
    ("sungold", "Sungold", 2, "medieval", 90.0, False),
    ("dustglass", "Dustglass", 2, "medieval", 20.0, False),
    ("preservers-salt", "Preserver's Salt", 2, "medieval", 30.0, False),
]

# (rule_id, name, tech_min, inputs, outputs, capacity_driver, labor_required)
# capacity_driver=None means universal (no endowment gate).
_GATHERING: list[tuple] = [
    ("dust-collection", "Dust Collection", "tribal", {}, {"dust": 1.0}, None, 1.0),
    ("sap-tapping", "Sap Tapping", "tribal", {}, {"sap": 2.0}, "sap_harvest", 2.0),
    ("phos-venting", "Phos Venting", "medieval", {}, {"phos": 1.0}, "phos_vent", 3.5),
    ("pitch-dredging", "Pitch Dredging", "medieval", {}, {"pitch": 1.0}, "pitch_depth", 4.0),
    ("ash-pilgrimage", "Ash Pilgrimage", "medieval", {}, {"ash": 1.0}, "ash_pilgrimage", 4.0),
    ("rime-collection", "Rime Collection", "medieval", {}, {"rime": 1.0}, "rime_collection", 4.0),
    ("mucus-harvest", "Mucus Harvest", "medieval", {}, {"mucus": 0.5}, "mucus_gland", 5.0),
    ("mold-excavation", "Mold Excavation", "medieval", {}, {"mold": 0.5}, "mold_deposit", 5.0),
]

_MINING: list[tuple] = [
    (
        f"{rid}-mining",
        f"{name.split(' ')[0]} Mining",
        "medieval",
        {},
        {rid: 1.5},
        f"{rid}_deposit",
        3.0,
    )
    for rid, name, _tier, _tech, _price, _per in _ELEMENTS
]

_RECIPES: list[tuple] = [
    # Recipes gate on the element deposit, so crafting specializes to the cities
    # that mine that element (inputs are not availability-gated by the engine).
    (
        "living-bronze-forging",
        "Living Bronze Forging",
        "medieval",
        {"cunu": 1.0, "sap": 1.0},
        {"living-bronze": 1.0},
        "cunu_deposit",
        5.0,
    ),
    (
        "soulstone-cutting",
        "Soulstone Cutting",
        "medieval",
        {"charon": 1.0, "mold": 1.0},
        {"soulstone": 1.0},
        "charon_deposit",
        6.0,
    ),
    (
        "dreamfire-brewing",
        "Dreamfire Brewing",
        "medieval",
        {"suhra": 1.0, "phos": 1.0},
        {"dreamfire": 1.0},
        "suhra_deposit",
        5.5,
    ),
    (
        "grave-lead-casting",
        "Grave Lead Casting",
        "medieval",
        {"plon": 1.0, "ash": 1.0},
        {"grave-lead": 1.0},
        "plon_deposit",
        5.0,
    ),
    # Crafter affinities from the lore: Sira-Pitch (wards, forgetting), Feron-Mucus
    # (forging, change), Aru-Mold (divinity, permanence), Sirael-Dust (foundation),
    # and the lore's own Preserver's Salt (Natra + Rime).
    (
        "wardsilver-casting",
        "Wardsilver Casting",
        "medieval",
        {"sira": 1.0, "pitch": 1.0},
        {"wardsilver": 1.0},
        "sira_deposit",
        5.5,
    ),
    (
        "shapeiron-forging",
        "Shapeiron Forging",
        "medieval",
        {"feron": 1.0, "mucus": 1.0},
        {"shapeiron": 1.0},
        "feron_deposit",
        5.0,
    ),
    (
        "sungold-refining",
        "Sungold Refining",
        "medieval",
        {"aru": 1.0, "mold": 1.0},
        {"sungold": 1.0},
        "aru_deposit",
        6.0,
    ),
    (
        "dustglass-firing",
        "Dustglass Firing",
        "medieval",
        {"sirael": 1.0, "dust": 1.0},
        {"dustglass": 1.0},
        "sirael_deposit",
        4.0,
    ),
    (
        "preservers-salt-curing",
        "Preserver's Salt Curing",
        "medieval",
        {"natra": 1.0, "rime": 1.0},
        {"preservers-salt": 1.0},
        "natra_deposit",
        4.0,
    ),
]

# Per-capita fantastical demand added on top of mundane demand, by tech level.
_DEMAND: dict[str, dict[str, Decimal]] = {
    "tribal": {"sap": Decimal("0.05")},
    "medieval": {
        "sap": Decimal("0.1"),
        "feron": Decimal("0.2"),
        "cunu": Decimal("0.1"),
        "living-bronze": Decimal("0.05"),
        "soulstone": Decimal("0.03"),
        "wardsilver": Decimal("0.02"),
        "shapeiron": Decimal("0.03"),
        "sungold": Decimal("0.01"),
        "dustglass": Decimal("0.05"),
        "preservers-salt": Decimal("0.05"),
    },
    "industrial": {
        "sap": Decimal("0.1"),
        "feron": Decimal("0.4"),
        "sirael": Decimal("0.2"),
        "living-bronze": Decimal("0.1"),
        "soulstone": Decimal("0.08"),
        "dreamfire": Decimal("0.08"),
        "grave-lead": Decimal("0.05"),
        "wardsilver": Decimal("0.03"),
        "shapeiron": Decimal("0.06"),
        "sungold": Decimal("0.02"),
        "dustglass": Decimal("0.1"),
        "preservers-salt": Decimal("0.05"),
    },
}


def fantastical_resources() -> list[Resource]:
    """All Eno fantastical resources (components + elements + stuffs)."""
    resources: list[Resource] = []
    for rid, name, tier, tech, price, perishable in _COMPONENTS + _ELEMENTS + _STUFFS:
        resources.append(
            Resource(
                resource_id=rid,
                name=name,
                tier=tier,
                tech_min=tech,
                base_price=Decimal(str(price)),
                transportable=True,
                perishable=perishable,
            )
        )
    return resources


def fantastical_rules() -> list[ProductionRule]:
    """All Eno production rules (gathering + mining + alchemical recipes)."""
    rules: list[ProductionRule] = []
    for rid, name, tech, inputs, outputs, driver, labor in _GATHERING + _MINING + _RECIPES:
        rules.append(
            ProductionRule(
                rule_id=rid,
                name=name,
                tech_min=tech,
                inputs={k: Decimal(str(v)) for k, v in inputs.items()},
                outputs={k: Decimal(str(v)) for k, v in outputs.items()},
                capacity_driver=driver,
                labor_required=Decimal(str(labor)),
            )
        )
    return rules


def with_fantastical_demand(profiles: list[DemandProfile]) -> list[DemandProfile]:
    """Return copies of ``profiles`` with Eno per-capita demand merged in."""
    merged: list[DemandProfile] = []
    for profile in profiles:
        tech_key = str(profile.tech)
        extra = _DEMAND.get(tech_key, {})
        per_capita = dict(profile.per_capita)
        per_capita.update({k: Decimal(str(v)) for k, v in extra.items()})
        merged.append(DemandProfile(tech=profile.tech, per_capita=per_capita))
    return merged


# resource_id -> "component" | "element" | "stuff" (the three catalog tiers).
ALCHEMICAL_CLASSES: dict[str, str] = {
    **{rid: "component" for rid, *_ in _COMPONENTS},
    **{rid: "element" for rid, *_ in _ELEMENTS},
    **{rid: "stuff" for rid, *_ in _STUFFS},
}


def alchemical_class(resource_id: str) -> str | None:
    """Return the alchemical tier of ``resource_id``, or None if mundane."""
    return ALCHEMICAL_CLASSES.get(resource_id)


__all__ = [
    "ALCHEMICAL_CLASSES",
    "alchemical_class",
    "fantastical_resources",
    "fantastical_rules",
    "with_fantastical_demand",
]
