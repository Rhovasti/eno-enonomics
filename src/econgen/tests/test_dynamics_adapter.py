"""Unit tests for the dynamics adapter (no Minsky dependency)."""

from decimal import Decimal
from typing import Dict

from ..dynamics import DynamicsConfig, build_dynamics_input
from ..dynamics.adapter import _build_trade_edges
from ..dynamics.state import StockSpec
from ..models import Operator, TechLevel


def _operator(operator_id: str, population: int = 1000) -> Operator:
    return Operator(
        operator_id=operator_id,
        name=operator_id,
        kind="city",
        tech=TechLevel.TRIBAL,
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
    demand: Dict[str, Dict[str, Decimal]] = {"a": {}}

    dynamics = build_dynamics_input(operators, supply, demand, DynamicsConfig())
    assert dynamics.stocks == []


class _FullyConnected:
    """Fake trade network: every city trades with every other at 50 km."""

    def __init__(self, cities: list) -> None:
        self.cities = cities

    def find_trade_partners(self, operator_id: str) -> list:
        return [c for c in self.cities if c != operator_id]

    def calculate_distance(self, op1_id: str, op2_id: str) -> Decimal:
        return Decimal("50")


def test_trade_partner_cap_applies_per_resource() -> None:
    """max_trade_partners caps edges per city *per resource*, not across resources.

    With a cap of 1, every resource must still get trade edges; previously the
    first resource (alphabetically) used up every city's single slot.
    """
    cities = ["a", "b", "c", "d"]
    stocks = [
        StockSpec(
            city=city,
            resource=resource,
            initial_stock=1.0,
            production_rate=1.0,
            consumption_rate=0.1,
        )
        for city in cities
        for resource in ("food", "wood")
    ]

    edges = _build_trade_edges(
        stocks, _FullyConnected(cities), DynamicsConfig(max_trade_partners=1)
    )

    edges_by_resource = {r: [e for e in edges if e.resource == r] for r in ("food", "wood")}
    assert len(edges_by_resource["food"]) == 2
    assert len(edges_by_resource["wood"]) == 2


def test_price_reference_stays_positive_with_zero_baseline() -> None:
    """A demanded-but-unproduced resource with a zero baseline must not get ref 0.

    The runner prices stocks as ``ref / (ref + stock)``; with every initial stock
    at 0 the mean reference was 0, giving 0/0.
    """
    operators = [_operator("a"), _operator("b")]
    supply: Dict[str, Dict[str, Decimal]] = {"a": {}, "b": {}}
    demand = {"a": {"sap": Decimal("100")}, "b": {"sap": Decimal("50")}}

    dynamics = build_dynamics_input(
        operators, supply, demand, DynamicsConfig(consumer_baseline_stock=0.0)
    )

    assert dynamics.stocks
    assert all(stock.price_reference > 0 for stock in dynamics.stocks)
