"""End-to-end tests for the simulation CLI."""

from pathlib import Path

from typer.testing import CliRunner

from ..cli import app

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_world.geojson"
EXPECTED_OUTPUTS = [
    "operators.jsonl",
    "capacities.jsonl",
    "demand.json",
    "supply.json",
    "prices.json",
    "trade_links.jsonl",
    "economic_analysis.md",
]


def test_run_writes_all_outputs(tmp_path: Path) -> None:
    """The full pipeline runs on the fixture and writes every output file."""
    result = CliRunner().invoke(
        app, ["run", "--input", str(FIXTURE), "--output", str(tmp_path), "--seed", "42"]
    )

    assert result.exit_code == 0, result.output
    for name in EXPECTED_OUTPUTS:
        assert (tmp_path / name).exists(), f"Missing output: {name}"

    operators = (tmp_path / "operators.jsonl").read_text().splitlines()
    assert len(operators) == 3

    trade_links = (tmp_path / "trade_links.jsonl").read_text().splitlines()
    assert len(trade_links) > 0, "Calibrated pipeline should produce trade links"
