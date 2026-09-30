"""Unit tests for the dynamics adapter (no Minsky dependency)."""

from decimal import Decimal

from ..models import Operator
from ..dynamics import DynamicsConfig, build_dynamics_input


def _operator(operator_id: str, population: int = 1000) -> Operator:
    return Operator(
        operator_id=operator_id,
        name=operator_id,
        kind="city",
        tech="tribal",
        coord=(60.0, 24.0),
        population=population,
    )


def test_adapter_proportional_rates_and_baseline() -> None:
    operators = [_operator("a", population=1000), _operator("b", population=500)]
    supply = {"a": {"food": Decimal("5")}, "b": {}}
    demand = {"a": {"food": Decimal("2000")}, "b": {"food": Decimal("1000")}}

    dynamics = build_dynamics_input(
        operators,
        supply,
        demand,
        DynamicsConfig(n_steps=10, initial_stock_multiplier=10.0, consumer_baseline_stock=50.0),
    )
    by_key = {(s.city, s.resource): s for s in dynamics.stocks}

    # producer: production = supply; consumption = per-capita demand; stock = prod * mult
    a = by_key[("a", "food")]
    assert a.production_rate == 5.0
    assert a.consumption_rate == 2.0  # 2000 / 1000
    assert a.initial_stock == 50.0  # 5 * 10

    # consumer (no production): drains at per-capita rate; starts at baseline
    b = by_key[("b", "food")]
    assert b.production_rate == 0.0
    assert b.consumption_rate == 2.0  # 1000 / 500
    assert b.initial_stock == 50.0  # consumer baseline

    assert dynamics.n_steps == 10
    assert dynamics.trade_edges == []


def test_adapter_resource_filter_restricts_scope() -> None:
    operators = [_operator("a")]
    supply = {"a": {"food": Decimal("5"), "iron": Decimal("2")}}
    demand = {"a": {"food": Decimal("1000")}}

    dynamics = build_dynamics_input(operators, supply, demand, DynamicsConfig(resources=["food"]))
    assert {s.resource for s in dynamics.stocks} == {"food"}


def test_adapter_skips_resources_with_no_supply_and_no_demand() -> None:
    operators = [_operator("a", population=0)]
    supply = {"a": {"food": Decimal("0")}}
    demand = {"a": {}}

    dynamics = build_dynamics_input(operators, supply, demand, DynamicsConfig())
    assert dynamics.stocks == []
