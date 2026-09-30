"""Tests for recipe input coupling in the dynamics layer (no Minsky dependency)."""

from decimal import Decimal
from pathlib import Path

from ..citystates.economy import make_economy
from ..cli_common import _compute_supply_and_demand
from ..demand import DemandCalculator, create_default_demand_profiles
from ..dynamics import DynamicsConfig, build_dynamics_input
from ..dynamics.adapter import recipe_input_rates
from ..models import Operator, TechLevel


def test_recipe_input_rates_from_default_rules() -> None:
    """Alchemical stuffs derive their per-unit input drains from their recipes."""
    _, rules_engine, _ = make_economy()
    rates = recipe_input_rates(rules_engine)

    assert rates["living-bronze"] == {"cunu": 1.0, "sap": 1.0}
    assert rates["soulstone"] == {"charon": 1.0, "mold": 1.0}
    assert rates["dreamfire"] == {"phos": 1.0, "suhra": 1.0}
    assert rates["grave-lead"] == {"ash": 1.0, "plon": 1.0}
    # Mundane crafting is coupled too: toolmaking consumes wood and stone,
    # farming consumes seed (1 seed per 3 food).
    assert rates["tools"] == {"stone": 1.0, "wood": 2.0}
    assert rates["food"] == {"seed": 1.0 / 3.0}
    # Gathered resources have no inputs and must be absent.
    assert "dust" not in rates
    assert "wood" not in rates


def test_recipe_input_rates_deterministic() -> None:
    _, rules_engine, _ = make_economy()
    assert recipe_input_rates(rules_engine) == recipe_input_rates(rules_engine)


def _operator(operator_id: str) -> Operator:
    return Operator(
        operator_id=operator_id,
        name=operator_id,
        kind="city",
        tech=TechLevel.MEDIEVAL,
        coord=(60.0, 24.0),
        population=1000,
    )


def test_adapter_couples_inputs_within_same_city_only() -> None:
    """A crafted stock drains inputs only when the input stock exists in that city."""
    _, rules_engine, _ = make_economy()
    operators = [_operator("a"), _operator("b")]
    supply: dict[str, dict[str, Decimal]] = {
        "a": {"living-bronze": Decimal(10), "cunu": Decimal(20), "sap": Decimal(5)},
        "b": {"living-bronze": Decimal(10)},  # crafts without local inputs
    }
    demand: dict[str, dict[str, Decimal]] = {"a": {}, "b": {"sap": Decimal(1)}}

    dynamics = build_dynamics_input(
        operators, supply, demand, DynamicsConfig(), rules_engine=rules_engine
    )

    by_key = {(s.city, s.resource): s for s in dynamics.stocks}
    assert by_key[("a", "living-bronze")].input_rates == {"cunu": 1.0, "sap": 1.0}
    assert by_key[("a", "cunu")].input_rates == {}
    # City b has no cunu stock, so only sap (present via demand) is coupled.
    assert by_key[("b", "living-bronze")].input_rates == {"sap": 1.0}


def test_adapter_without_rules_engine_leaves_inputs_empty() -> None:
    operators = [_operator("a")]
    supply = {"a": {"living-bronze": Decimal(10), "cunu": Decimal(20)}}
    demand: dict[str, dict[str, Decimal]] = {"a": {}}

    dynamics = build_dynamics_input(operators, supply, demand, DynamicsConfig())

    assert all(stock.input_rates == {} for stock in dynamics.stocks)


def test_dynamics_pipeline_passes_final_demand_only() -> None:
    """The dynamics layer drains recipe inputs itself, so it must get final demand.

    Calibration still sizes supply for final plus input demand, but the demand
    handed to the Minsky builder must exclude the inputs; otherwise every input
    stock is drained twice (once as consumption, once by the recipe flows).
    """
    fixture = Path(__file__).parent / "fixtures" / "tiny_world.geojson"
    operators, supply, demand, _, _, taxonomy, _ = _compute_supply_and_demand(
        [fixture], None, None, True
    )

    final = DemandCalculator(taxonomy, create_default_demand_profiles()).calculate_all_demand(
        operators
    )
    assert demand == final

    # Supply is still calibrated to cover the inputs that production consumes:
    # iron ore supply covers steel-making's input on top of final demand.
    ore_supply = sum(ops.get("iron-ore", Decimal(0)) for ops in supply.values())
    ore_final = sum(ops.get("iron-ore", Decimal(0)) for ops in final.values())
    assert ore_supply > ore_final
