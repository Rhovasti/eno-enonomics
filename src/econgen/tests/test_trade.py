"""Tests for trade flow solving."""

from decimal import Decimal

from ..models import Operator, SimulationConfig, TechLevel
from ..trade import TradeNetwork


def _city(operator_id: str, lon: float) -> Operator:
    return Operator(
        operator_id=operator_id,
        name=operator_id,
        kind="city",
        tech=TechLevel.MEDIEVAL,
        coord=(0.0, lon),
        population=1000,
    )


def test_only_net_surplus_is_exported() -> None:
    """A producer keeps what it consumes and exports only the remainder."""
    network = TradeNetwork([_city("farm", 0.0), _city("town", 1.0)], SimulationConfig())
    supply = {"farm": {"food": Decimal(100)}}
    demand = {"farm": {"food": Decimal(70)}, "town": {"food": Decimal(50)}}
    prices = {"farm": {"food": Decimal(2)}, "town": {"food": Decimal(10)}}

    links = network.solve_trade_flows(supply, demand, prices)

    assert len(links) == 1
    assert links[0].source_id == "farm"
    assert links[0].quantity == Decimal(30)


def test_self_sufficient_operator_does_not_import() -> None:
    """An operator whose own supply covers its demand has nothing to import."""
    network = TradeNetwork([_city("a", 0.0), _city("b", 1.0)], SimulationConfig())
    supply = {"a": {"food": Decimal(100)}, "b": {"food": Decimal(40)}}
    demand = {"a": {"food": Decimal(10)}, "b": {"food": Decimal(40)}}
    prices = {"a": {"food": Decimal(2)}, "b": {"food": Decimal(10)}}

    assert network.solve_trade_flows(supply, demand, prices) == []
