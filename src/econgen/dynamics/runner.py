"""Run a dynamics simulation: build -> integrate -> sample -> persist."""

import json
from pathlib import Path

from .builder import PRICE_ALPHA, MinskyModelBuilder
from .client import MinskyClient
from .state import DynamicsInput, SimulationResult


def simulate(client: MinskyClient, dynamics_input: DynamicsInput) -> SimulationResult:
    """Build the model from ``dynamics_input`` and integrate it forward.

    Args:
        client: Connected (or connectable) MinskyClient.
        dynamics_input: Stocks to simulate and step count.

    Returns:
        SimulationResult with per-step time and per-stock series.
    """
    minsky = client.connect()
    client.new_model()

    builder = MinskyModelBuilder(minsky)
    builder.build(dynamics_input)

    seed = dynamics_input.seed if dynamics_input.seed is not None else 0
    minsky.running(True)
    minsky.srand(seed)
    minsky.reset()

    time: list[float] = []
    series: dict[str, list[float]] = {name: [] for name in builder.series}
    prices: dict[str, list[float]] = {name: [] for name in builder.series}
    # Recompute the bounded scarcity price from each step's stock (matches builder).
    specs = {f"{s.city}/{s.resource}": s for s in dynamics_input.stocks}
    for _ in range(dynamics_input.n_steps):
        minsky.step()
        time.append(float(minsky.t()))
        for name, value_id in builder.series.items():
            stock = float(minsky.variableValues[value_id].value())
            series[name].append(stock)
            spec = specs[name]
            scarcity = spec.price_reference / (spec.price_reference + stock)
            prices[name].append(spec.base_price * (1 + PRICE_ALPHA * scarcity))

    return SimulationResult(time=time, series=series, prices=prices, n_steps=dynamics_input.n_steps)


def write_outputs(
    output_dir: Path,
    dynamics_input: DynamicsInput,
    result: SimulationResult,
    client: MinskyClient,
) -> None:
    """Persist the .mky model + series/input JSON under ``output_dir``.

    Follows the Enonomics output convention (JSON for nested aggregates).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result.model_path = client.save(output_dir / "model.mky")

    (output_dir / "dynamics_series.json").write_text(
        json.dumps(
            {"time": result.time, "series": result.series, "prices": result.prices},
            indent=2,
        )
    )
    (output_dir / "dynamics_input.json").write_text(dynamics_input.model_dump_json(indent=2))
