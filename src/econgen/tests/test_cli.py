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


def test_validate_succeeds_on_valid_input() -> None:
    """validate exits 0 when every input file loads."""
    result = CliRunner().invoke(app, ["validate", "--input", str(FIXTURE)])

    assert result.exit_code == 0, result.output
    assert "3 valid operators" in result.output


def test_validate_fails_on_missing_file(tmp_path: Path) -> None:
    """validate exits non-zero when an input file does not exist."""
    missing = tmp_path / "missing.geojson"

    result = CliRunner().invoke(app, ["validate", "--input", str(missing)])

    assert result.exit_code == 1, result.output
    assert "missing.geojson" in result.output


def test_validate_checks_every_file_before_failing(tmp_path: Path) -> None:
    """A bad file does not stop the remaining files being validated."""
    bad = tmp_path / "bad.geojson"
    bad.write_text("not json")

    result = CliRunner().invoke(app, ["validate", "--input", str(bad), "--input", str(FIXTURE)])

    assert result.exit_code == 1, result.output
    assert "bad.geojson" in result.output
    assert "3 valid operators" in result.output
