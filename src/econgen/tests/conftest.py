"""Shared pytest fixtures for dynamics and citystate tests."""

import os
from pathlib import Path
from typing import List

import pytest

from ..citystates.parser import CitystateSpec, load_citystates
from ..dynamics.client import MinskyClient, MinskyUnavailable
from ..paths import citystates_dir

# Synthetic citystate profiles bundled with the tests, so CI can exercise the parser
# and endowment inference without the external Eno-Worldbuilder2 corpus.
BUNDLED_CITYSTATES_DIR = Path(__file__).parent / "fixtures" / "citystates"


@pytest.fixture(scope="module")
def minsky_client():
    """A connected MinskyClient, or skip the test if pyminsky is unavailable."""
    client = MinskyClient()
    try:
        client.connect()
    except MinskyUnavailable as exc:
        # Reason: the Minsky CI job sets ENO_REQUIRE_MINSKY so a broken install
        # fails loudly instead of silently skipping every dynamics test.
        if os.environ.get("ENO_REQUIRE_MINSKY"):
            pytest.fail(f"ENO_REQUIRE_MINSKY is set but pyminsky is unavailable: {exc}")
        pytest.skip("pyminsky extension not available in this environment")
    return client


def _dir_readable(path: Path) -> bool:
    # CI runners cannot stat paths under /root (PermissionError), so the
    # existence probe itself must be guarded, not just the tests.
    try:
        return path.is_dir()
    except OSError:
        return False


@pytest.fixture(scope="session")
def corpus_dir() -> Path:
    """The real citystate corpus ($ENO_CITYSTATES_DIR), or skip if unavailable."""
    directory = citystates_dir()
    if not _dir_readable(directory):
        pytest.skip("citystates profile folder not present")
    return directory


@pytest.fixture(scope="session")
def corpus_specs(corpus_dir: Path) -> List[CitystateSpec]:
    """All specs from the real citystate corpus (skips when it is unavailable)."""
    return load_citystates(corpus_dir)


@pytest.fixture(scope="session", params=["bundled", "corpus"])
def all_specs(request: pytest.FixtureRequest) -> List[CitystateSpec]:
    """Specs for invariant tests: the bundled fixtures, plus the real corpus if present."""
    if request.param == "bundled":
        return load_citystates(BUNDLED_CITYSTATES_DIR)
    return request.getfixturevalue("corpus_specs")
