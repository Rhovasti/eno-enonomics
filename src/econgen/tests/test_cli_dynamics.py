"""Smoke tests for the ``simulate`` CLI command (Minsky dynamics)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from .. import cli_dynamics
from ..cli import app
from ..dynamics.client import MinskyUnavailable

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_world.geojson"


def _simulate(output: Path, *extra: str):
    """Run ``simulate`` on the tiny fixture world."""
    args = ["simulate", "--input", str(FIXTURE), "--output", str(output), "--seed", "42"]
    return CliRunner().invoke(app, [*args, *extra])


def test_simulate_fails_cleanly_without_minsky(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pipeline builds its stocks, then reports a missing Minsky engine and exits 1."""

    def no_minsky(*args, **kwargs):
        raise MinskyUnavailable("pyminsky not found")

    monkeypatch.setattr(cli_dynamics, "run_dynamics_simulation", no_minsky)

    result = _simulate(tmp_path)

    assert result.exit_code == 1
    assert "Building" in result.output  # got as far as the engine call
    assert "pyminsky not found" in result.output


def test_simulate_fails_when_no_stocks_match(tmp_path: Path) -> None:
    """Restricting to a resource nobody produces or needs leaves nothing to simulate."""
    result = _simulate(tmp_path, "--resource", "no-such-resource")

    assert result.exit_code == 1
    assert "No stocks to simulate" in result.output


def test_simulate_writes_outputs_with_minsky(minsky_client, tmp_path: Path) -> None:
    """With Minsky available, simulate integrates the model and writes its outputs."""
    # Reason: one resource keeps the model at 3 stocks; the full tiny world (62 stocks)
    # takes over two minutes to build in Minsky.
    result = _simulate(tmp_path, "--steps", "10", "--resource", "food")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "model.mky").exists()
    assert (tmp_path / "dynamics_input.json").exists()
    data = json.loads((tmp_path / "dynamics_series.json").read_text())
    assert len(data["time"]) > 1
    assert data["series"], "expected at least one simulated series"
