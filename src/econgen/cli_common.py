"""Shared CLI plumbing: Typer app, console, configuration and pipeline helpers.

Command modules (``cli``, ``cli_dynamics``, ``cli_citystates``) all register
their commands on the single :data:`app` defined here.
"""

import logging
from decimal import Decimal
from pathlib import Path

import typer
import yaml
from rich.console import Console

from .calibration import calibrate_with_input_demand
from .capacity import CapacityCalculator
from .demand import DemandCalculator, create_default_demand_profiles
from .dynamics.state import DynamicsConfig
from .io_geojson import GeoJSONLoader
from .models import DemandProfile, ProductionRule, Resource, SimulationConfig
from .rules import RulesEngine, create_default_rules
from .taxonomy import ResourceTaxonomy, create_default_taxonomy

# Initialize Typer app and Rich console (shared by all command modules)
app = typer.Typer(
    help="Economic Worldbuilding Generator - Deterministic economic simulation for GeoJSON data",
    add_completion=False,
)
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _load_configuration(
    config_path: Path | None,
) -> tuple[SimulationConfig, list[Resource], list[ProductionRule], list[DemandProfile]]:
    """Load configuration or use defaults."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        # Parse configuration sections
        config = SimulationConfig(**config_data.get("simulation", {}))

        resources = [Resource(**r) for r in config_data.get("resources", [])]
        if not resources:
            resources = list(create_default_taxonomy().resources.values())

        rules = [ProductionRule(**r) for r in config_data.get("rules", [])]
        if not rules:
            rules = create_default_rules()

        demand_profiles = [DemandProfile(**d) for d in config_data.get("demand_profiles", [])]
        if not demand_profiles:
            demand_profiles = create_default_demand_profiles()

    else:
        # Use defaults
        console.print("⚠️  No config file provided, using defaults")
        config = SimulationConfig()
        resources = list(create_default_taxonomy().resources.values())
        rules = create_default_rules()
        demand_profiles = create_default_demand_profiles()

    return config, resources, rules, demand_profiles


def _load_dynamics_config(config_path: Path | None) -> DynamicsConfig:
    """Load the optional ``dynamics:`` section of a configuration file."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        if config_data and isinstance(config_data.get("dynamics"), dict):
            return DynamicsConfig(**config_data["dynamics"])
    return DynamicsConfig()


def _calculate_supply_from_capacities(
    capacities: list, operators: list, rules_engine: RulesEngine
) -> dict[str, dict[str, Decimal]]:
    """Calculate supply quantities from production capacities."""
    supply: dict[str, dict[str, Decimal]] = {}

    for capacity in capacities:
        if capacity.operator_id not in supply:
            supply[capacity.operator_id] = {}

        # Get the actual rule to access its outputs
        rule = rules_engine.get_rule(capacity.rule_id)
        if not rule:
            continue

        # Calculate base production
        production = capacity.max_rate * capacity.efficiency

        # Iterate through actual rule outputs (proper resource IDs)
        for resource_id, output_ratio in rule.outputs.items():
            # Scale production by output ratio
            resource_production = production * output_ratio

            if resource_id in supply[capacity.operator_id]:
                supply[capacity.operator_id][resource_id] += resource_production
            else:
                supply[capacity.operator_id][resource_id] = resource_production

    return supply


def _compute_supply_and_demand(
    input_paths: list[Path],
    config_path: Path | None,
    seed: int | None,
    strict: bool,
) -> tuple[list, dict, dict, DynamicsConfig, SimulationConfig, ResourceTaxonomy, RulesEngine]:
    """Run the static pipeline up to calibrated supply/demand for the dynamics layer.

    Mirrors the ``run`` pipeline (including input-demand calibration) and returns
    the *final* demand, so downstream stock/flow drains represent production
    inputs exactly once.
    """
    sim_config, resources, rules, demand_profiles = _load_configuration(config_path)
    dynamics_config = _load_dynamics_config(config_path)
    loader = GeoJSONLoader(strict=strict)
    operators = loader.load_operators(input_paths)
    if not operators:
        console.print("❌ [red]No operators loaded. Check input files.[/red]")
        raise typer.Exit(1)

    taxonomy = ResourceTaxonomy(resources)
    rules_engine = RulesEngine(rules)
    capacity_calc = CapacityCalculator(rules_engine)
    demand_calc = DemandCalculator(taxonomy, demand_profiles)
    capacities = capacity_calc.calculate_all_capacities(operators)
    demand = demand_calc.calculate_all_demand(operators)

    # Calibrate so world supply matches final demand plus production inputs.
    # Reason: return only the final demand; the dynamics builder drains recipe
    # inputs itself, so the calibrated total (final + inputs) would count them twice.
    capacities, _ = calibrate_with_input_demand(
        capacities, rules_engine, demand, sim_config.supply_demand_ratio
    )

    supply = _calculate_supply_from_capacities(capacities, operators, rules_engine)
    return operators, supply, demand, dynamics_config, sim_config, taxonomy, rules_engine


def _resolve_dynamics_config(
    dynamics_config: DynamicsConfig,
    steps: int | None,
    seed: int | None,
    resource: str | None,
) -> DynamicsConfig:
    """Apply CLI overrides (--steps/--seed/--resource) to the dynamics config."""
    updates: dict = {}
    if steps is not None:
        updates["n_steps"] = steps
    if seed is not None:
        updates["seed"] = seed
    if resource is not None:
        updates["resources"] = [resource]
    return dynamics_config.model_copy(update=updates) if updates else dynamics_config
