"""Tests that external paths come from environment variables, not hardcoded values."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from .. import paths
from ..cli import app
from ..dynamics import DynamicsConfig
from ..dynamics.client import MinskyClient


def test_defaults_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without overrides, the documented defaults are used."""
    for name in (paths.ENV_MINSKY_ROOT, paths.ENV_CITYSTATES_DIR, paths.ENV_WORLDBUILDER_DIR):
        monkeypatch.delenv(name, raising=False)

    assert paths.minsky_root() == paths.DEFAULT_MINSKY_ROOT
    assert paths.citystates_dir() == Path(paths.DEFAULT_CITYSTATES_DIR)
    assert paths.worldbuilder_dir() == Path(paths.DEFAULT_WORLDBUILDER_DIR)


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Each external path can be overridden with its environment variable."""
    monkeypatch.setenv(paths.ENV_MINSKY_ROOT, str(tmp_path / "minsky"))
    monkeypatch.setenv(paths.ENV_CITYSTATES_DIR, str(tmp_path / "profiles"))
    monkeypatch.setenv(paths.ENV_WORLDBUILDER_DIR, str(tmp_path / "wb"))

    assert paths.minsky_root() == str(tmp_path / "minsky")
    assert paths.citystates_dir() == tmp_path / "profiles"
    assert paths.worldbuilder_dir() == tmp_path / "wb"


def test_minsky_consumers_use_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """MinskyClient and DynamicsConfig pick up ENO_MINSKY_ROOT by default."""
    monkeypatch.setenv(paths.ENV_MINSKY_ROOT, str(tmp_path))

    assert MinskyClient().root == str(tmp_path)
    assert DynamicsConfig().minsky_root == str(tmp_path)


def test_citystates_command_reads_dir_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """citystate commands default to ENO_CITYSTATES_DIR when --citystates-dir is absent."""
    from .. import cli_citystates

    monkeypatch.setenv(paths.ENV_CITYSTATES_DIR, str(tmp_path / "profiles"))
    seen: list = []

    def fake_load(directory: Path) -> list:
        seen.append(Path(directory))
        raise RuntimeError("stop after recording the directory")

    monkeypatch.setattr(cli_citystates, "load_citystates", fake_load)

    CliRunner().invoke(app, ["citystate-governance", "--output", str(tmp_path / "out")])

    assert seen == [tmp_path / "profiles"]
