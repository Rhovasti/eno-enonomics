"""Tests for the Minsky model builder (requires the pyminsky extension)."""

from ..dynamics.builder import MinskyModelBuilder
from ..dynamics.state import DynamicsInput, StockSpec


def _one_stock(production: float = 5.0, consumption: float = 2.0) -> DynamicsInput:
    return DynamicsInput(
        stocks=[
            StockSpec(
                city="a",
                resource="food",
                initial_stock=10.0,
                production_rate=production,
                consumption_rate=consumption,
            )
        ],
        n_steps=5,
        seed=0,
    )


def test_builder_creates_stock_and_series_mapping(minsky_client) -> None:
    dynamics = _one_stock()
    minsky = minsky_client.connect()
    minsky_client.new_model()

    builder = MinskyModelBuilder(minsky)
    builder.build(dynamics)

    assert "a/food" in builder.series
    value_id = builder.series["a/food"]
    assert value_id.startswith(":s")
    assert value_id in list(minsky.variableValues.keys())


def test_builder_handles_multiple_stocks(minsky_client) -> None:
    specs = [
        StockSpec(
            city=f"c{i}",
            resource="food",
            initial_stock=10.0,
            production_rate=float(i + 1),
            consumption_rate=1.0,
        )
        for i in range(5)
    ]
    dynamics = DynamicsInput(stocks=specs, n_steps=3, seed=0)
    minsky = minsky_client.connect()
    minsky_client.new_model()

    builder = MinskyModelBuilder(minsky)
    builder.build(dynamics)

    assert len(builder.series) == 5
