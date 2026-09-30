"""Smoke tests for the citystate CLI commands, run on the bundled synthetic profiles."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ..citystates import simulator
from ..cli import app
from ..dynamics.client import MinskyUnavailable
from .conftest import BUNDLED_CITYSTATES_DIR

CITIES = ["Duskwater", "Emberfold", "Greenhollow", "Highcrag", "Nowhereton", "Saltmere"]


def _invoke(command: str, output: Path, *extra: str):
    """Run a citystate command against the bundled profiles."""
    args = [command, "--citystates-dir", str(BUNDLED_CITYSTATES_DIR), "--output", str(output)]
    return CliRunner().invoke(app, [*args, *extra])


def test_citystate_sim_writes_a_profile_per_city(tmp_path: Path) -> None:
    """citystate-sim writes a markdown and JSON profile for every city, plus an index."""
    result = _invoke("citystate-sim", tmp_path)

    assert result.exit_code == 0, result.output
    for city in CITIES:
        assert (tmp_path / f"{city}.md").exists()
        profile = json.loads((tmp_path / f"{city}.json").read_text())
        assert profile["name"] == city
    assert (tmp_path / "index.md").exists()


def test_citystate_sim_respects_limit(tmp_path: Path) -> None:
    """--limit profiles only the first N cities."""
    result = _invoke("citystate-sim", tmp_path, "--limit", "2")

    assert result.exit_code == 0, result.output
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_citystate_financial_writes_analyses(tmp_path: Path) -> None:
    """citystate-financial writes per-city analyses and the Utaia dominion summary."""
    result = _invoke("citystate-financial", tmp_path)

    assert result.exit_code == 0, result.output
    for city in CITIES:
        assert (tmp_path / f"{city}.md").exists()
        assert (tmp_path / f"{city}.json").exists()
    for name in ("utai_dominion.md", "utai_dominion.json", "index.md"):
        assert (tmp_path / name).exists(), name


def test_citystate_governance_assigns_every_city(tmp_path: Path) -> None:
    """citystate-governance writes a record per city, plus the dam settlement it adds."""
    result = _invoke("citystate-governance", tmp_path)

    assert result.exit_code == 0, result.output
    records = {p.stem for p in tmp_path.glob("*.json")}
    assert set(CITIES) <= records
    assert len(records) == len(CITIES) + 1  # the dam settlement
    assert (tmp_path / "index.md").exists()


def test_citystate_chronicle_renders_matching_histories(tmp_path: Path) -> None:
    """citystate-chronicle renders histories of known cities and skips unknown ones."""
    histories = tmp_path / "histories"
    histories.mkdir()
    history = {
        "founded_cycle": 900,
        "time": [0, 49, 98],
        "population": [1000.0, 1200.0, 1400.0],
        "tech": [0.5, 1.0, 1.5],
        "resources": ["food"],
        "stocks": {"food": [10.0, 20.0, 30.0]},
        "trade": {"food": [0.0, 0.0, 0.0]},
    }
    for name in ("Highcrag", "Atlantis"):
        (histories / f"{name}.json").write_text(json.dumps({**history, "name": name}))
    output = tmp_path / "chronicles"

    result = _invoke("citystate-chronicle", output, "--histories-dir", str(histories))

    assert result.exit_code == 0, result.output
    assert [p.name for p in output.iterdir()] == ["Highcrag.md"]
    assert (output / "Highcrag.md").read_text().startswith("# Economic Chronicle: Highcrag")


def test_citystate_dynamic_fails_cleanly_without_minsky(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """citystate-dynamic reports a missing Minsky engine and exits non-zero."""

    def no_minsky(*args, **kwargs):
        raise MinskyUnavailable("pyminsky not found")

    monkeypatch.setattr(simulator, "simulate_city", no_minsky)

    result = _invoke("citystate-dynamic", tmp_path, "--limit", "1")

    assert result.exit_code == 1
    assert "pyminsky not found" in result.output


@pytest.mark.parametrize(
    "command",
    ["citystate-sim", "citystate-financial", "citystate-governance", "citystate-chronicle"],
)
def test_citystate_commands_fail_on_missing_profiles(command: str, tmp_path: Path) -> None:
    """Every citystate command exits non-zero when the profile folder does not exist."""
    missing = tmp_path / "no-such-folder"
    args = [command, "--citystates-dir", str(missing), "--output", str(tmp_path / "out")]

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 1, result.output
