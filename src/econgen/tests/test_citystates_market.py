"""Tests for the input-aware world market prices (no Minsky dependency)."""

from typing import Dict

from ..citystates.economy import make_economy
from ..citystates.market import ALCHEMICAL_MARGIN, _apply_input_floors, compute_market_prices
from ..citystates.parser import CitystateSpec


def test_input_floor_binds_when_components_are_scarce() -> None:
    """A stuff priced below (1+margin) * input cost is raised to the floor."""
    prices = {"cunu": 30.0, "sap": 25.0, "living-bronze": 40.0}
    reqs = {"living-bronze": {"cunu": 1.0, "sap": 1.0}}

    floored = _apply_input_floors(prices, reqs)

    expected = (1.0 + ALCHEMICAL_MARGIN) * (30.0 + 25.0)
    assert floored["living-bronze"] == expected
    # Components themselves are unchanged.
    assert floored["cunu"] == 30.0
    assert floored["sap"] == 25.0


def test_input_floor_does_not_bind_when_scarcity_price_is_higher() -> None:
    prices = {"cunu": 5.0, "sap": 4.0, "living-bronze": 90.0}
    reqs = {"living-bronze": {"cunu": 1.0, "sap": 1.0}}

    floored = _apply_input_floors(prices, reqs)

    assert floored["living-bronze"] == 90.0


def test_input_floor_propagates_along_chains() -> None:
    """wood -> tools -> steel: a wood spike raises tools, then steel, then machinery."""
    reqs = {
        "tools": {"wood": 2.0, "stone": 1.0},
        "steel": {"iron-ore": 1.5, "tools": 1.0},
    }
    prices = {"wood": 20.0, "stone": 1.0, "iron-ore": 2.0, "tools": 5.0, "steel": 10.0}

    floored = _apply_input_floors(prices, reqs)

    tools_floor = 1.25 * (2 * 20.0 + 1.0)
    steel_floor = 1.25 * (1.5 * 2.0 + tools_floor)
    assert floored["tools"] == tools_floor
    assert floored["steel"] == steel_floor


def test_input_floor_skips_resources_with_unpriced_inputs() -> None:
    prices = {"cunu": 5.0, "living-bronze": 40.0}  # sap never priced
    reqs = {"living-bronze": {"cunu": 1.0, "sap": 1.0}}

    floored = _apply_input_floors(prices, reqs)

    assert floored["living-bronze"] == 40.0


def test_input_floors_deterministic() -> None:
    prices = {"cunu": 30.0, "sap": 25.0, "living-bronze": 10.0}
    reqs = {"living-bronze": {"cunu": 1.0, "sap": 1.0}}
    assert _apply_input_floors(prices, reqs) == _apply_input_floors(prices, reqs)


def _spec(name: str, population: int, longitude: float, tags: list) -> CitystateSpec:
    return CitystateSpec(
        name=name,
        founded_cycle=100,
        population=population,
        growth_rate=0.01,
        temporal_state="Day",
        valley="Day",
        latitude=45.0,
        longitude=longitude,
        tags=tags,
    )


def test_compute_market_prices_inputs_cover_recipe_cost() -> None:
    """End-to-end world prices: every stuff at least repays its recipe inputs."""
    taxonomy, rules_engine, demand_calc = make_economy()
    specs = [
        _spec("Aira", 20000, -30.0, ["forest"]),
        _spec("Aiya", 30000, 30.0, ["industrial"]),
        _spec("Alebuo", 10000, -45.0, ["mountain"]),
    ]

    prices: Dict[str, float] = compute_market_prices(specs, taxonomy, rules_engine, demand_calc)

    # Both living-bronze inputs are priced here, so its floor must hold.
    assert "cunu" in prices and "sap" in prices
    assert prices["living-bronze"] >= (1.0 + ALCHEMICAL_MARGIN) * (prices["cunu"] + prices["sap"])
    # Stuffs whose inputs are not all priced (e.g. soulstone needs charon)
    # simply keep their scarcity price — still present and finite.
    assert prices["soulstone"] > 0.0
    # Deterministic.
    again = compute_market_prices(specs, taxonomy, rules_engine, demand_calc)
    assert prices == again
