"""Tests that the bundled YAML config matches the built-in defaults."""

from pathlib import Path

import pytest

from ..cli import _load_configuration
from ..demand import create_default_demand_profiles
from ..models import SimulationConfig
from ..rules import create_default_rules
from ..taxonomy import create_default_taxonomy

CONFIG_PATH = Path(__file__).parents[3] / "config" / "econ.yaml"


@pytest.fixture(scope="module")
def yaml_config():
    """Load config/econ.yaml the same way the CLI does."""
    return _load_configuration(CONFIG_PATH)


def test_simulation_settings_match_defaults(yaml_config) -> None:
    """Simulation parameters in the YAML equal SimulationConfig defaults."""
    config, _, _, _ = yaml_config
    assert config == SimulationConfig()


def test_resources_match_default_taxonomy(yaml_config) -> None:
    """The YAML defines exactly the default resources, field for field."""
    _, resources, _, _ = yaml_config
    yaml_resources = {r.resource_id: r for r in resources}
    assert yaml_resources == create_default_taxonomy().resources


def test_rules_match_default_rules(yaml_config) -> None:
    """The YAML defines exactly the default production rules, field for field."""
    _, _, rules, _ = yaml_config
    assert {r.rule_id: r for r in rules} == {
        r.rule_id: r for r in create_default_rules()
    }


def test_demand_profiles_match_defaults(yaml_config) -> None:
    """The YAML demand profiles equal the default profiles."""
    _, _, _, profiles = yaml_config
    defaults = create_default_demand_profiles()
    assert {p.tech: p for p in profiles} == {p.tech: p for p in defaults}
