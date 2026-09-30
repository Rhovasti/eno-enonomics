"""End-to-end tests for the dynamics runner (requires the pyminsky extension)."""

import json
import math

from ..dynamics import DynamicsInput, StockSpec, TradeEdge, simulate, write_outputs


def _proportional_stock() -> DynamicsInput:
    # dS/dt = 5 - 0.5*S, S0=2  ->  S(t) = 10 - 8*exp(-0.5*t)  (steady state 10)
    return DynamicsInput(
        stocks=[
            StockSpec(
                city="a",
                resource="food",
                initial_stock=2.0,
                production_rate=5.0,
                consumption_rate=0.5,
            )
        ],
        n_steps=30,
        seed=0,
    )


def test_simulate_proportional_stock_matches_analytic(minsky_client) -> None:
    result = simulate(minsky_client, _proportional_stock())
    assert len(result.time) == 30
    series = result.series["a/food"]
    assert len(series) == 30
    t_last, v_last = result.time[-1], series[-1]
    expected = 10.0 - 8.0 * math.exp(-0.5 * t_last)
    assert abs(v_last - expected) < 1e-3


def test_simulate_proportional_stock_never_goes_negative(minsky_client) -> None:
    result = simulate(minsky_client, _proportional_stock())
    assert all(v >= -1e-9 for v in result.series["a/food"])


def test_simulate_trade_redistributes_from_producer_to_consumer(minsky_client) -> None:
    # Producer A starts full (10), consumer B starts empty (0); trade moves surplus.
    dynamics = DynamicsInput(
        stocks=[
            StockSpec(
                city="a",
                resource="food",
                initial_stock=10.0,
                production_rate=5.0,
                consumption_rate=0.5,
            ),
            StockSpec(
                city="b",
                resource="food",
                initial_stock=0.0,
                production_rate=0.0,
                consumption_rate=0.5,
            ),
        ],
        trade_edges=[TradeEdge(source="a", dest="b", resource="food", conductance=0.2)],
        n_steps=40,
        seed=0,
    )
    result = simulate(minsky_client, dynamics)
    a, b = result.series["a/food"], result.series["b/food"]
    # producer shipped surplus out, consumer received some; both stay non-negative
    assert a[-1] < 10.0
    assert b[-1] > 0.0
    assert all(v >= -1e-9 for v in a)
    assert all(v >= -1e-9 for v in b)


def test_write_outputs_creates_files(minsky_client, tmp_path) -> None:
    dynamics = _proportional_stock()
    result = simulate(minsky_client, dynamics)
    write_outputs(tmp_path, dynamics, result, minsky_client)

    assert (tmp_path / "model.mky").is_file()
    assert (tmp_path / "dynamics_series.json").is_file()
    assert (tmp_path / "dynamics_input.json").is_file()
    data = json.loads((tmp_path / "dynamics_series.json").read_text())
    assert "a/food" in data["series"]
    assert len(data["series"]["a/food"]) == 30
