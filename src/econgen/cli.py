"""CLI entry point for the economic worldbuilding generator."""

import json
import time
from pathlib import Path

import typer
import yaml
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Register the extended command modules on the shared app. Imported at the
# bottom of the module graph so `run` stays the first command in `--help`.
from . import cli_citystates, cli_dynamics  # noqa: F401
from .calibration import calibrate_with_input_demand
from .capacity import CapacityCalculator

# Shared app/console/configuration helpers (single Typer app for all modules)
from .cli_common import (
    _calculate_supply_from_capacities,
    _load_configuration,
    app,
    console,
)
from .demand import DemandCalculator
from .io_geojson import GeoJSONLoader
from .paths import minsky_root
from .pricing import PriceCalculator
from .report import ReportGenerator
from .rules import RulesEngine
from .taxonomy import ResourceTaxonomy
from .trade import TradeNetwork
from .util import set_seed


@app.command()
def run(
    input_paths: list[Path] = typer.Option(
        ...,
        "--input",
        "-i",
        help="GeoJSON input files containing city/operator data",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration YAML file (uses defaults if not provided)",
        exists=True,
    ),
    output_dir: Path = typer.Option(
        Path("out/econ"), "--output", "-o", help="Output directory for results"
    ),
    seed: int | None = typer.Option(
        None, "--seed", "-s", help="Random seed for deterministic results"
    ),
    strict: bool = typer.Option(
        True, "--strict/--no-strict", help="Strict validation mode (fail on errors vs warnings)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """Run complete economic simulation pipeline."""
    start_time = time.time()

    # Set up logging
    if verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    # Display header
    console.print(
        Panel.fit(
            "[bold blue]Economic Worldbuilding Generator[/bold blue]\n"
            "[dim]Deterministic economic simulation for GeoJSON data[/dim]",
            border_style="blue",
        )
    )

    try:
        # Set random seed for determinism
        if seed is not None:
            set_seed(seed)
            console.print(f"🎲 Random seed set to: [bold]{seed}[/bold]")

        # Load configuration
        config, resources, rules, demand_profiles = _load_configuration(config_path)
        console.print(f"⚙️  Loaded configuration: {len(resources)} resources, {len(rules)} rules")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"📁 Output directory: [bold]{output_dir}[/bold]")

        # Initialize progress tracking
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            # Load operators from GeoJSON
            task = progress.add_task("Loading GeoJSON data...", total=None)
            loader = GeoJSONLoader(strict=strict)
            operators = loader.load_operators(input_paths)
            progress.update(task, description=f"✅ Loaded {len(operators)} operators")
            progress.remove_task(task)

            if not operators:
                console.print("❌ [red]No operators loaded. Check input files.[/red]")
                raise typer.Exit(1)

            # Initialize core components
            task = progress.add_task("Initializing simulation components...", total=None)
            taxonomy = ResourceTaxonomy(resources)
            rules_engine = RulesEngine(rules)
            capacity_calc = CapacityCalculator(rules_engine)
            demand_calc = DemandCalculator(taxonomy, demand_profiles)
            trade_network = TradeNetwork(operators, config)
            price_calc = PriceCalculator(taxonomy, config)
            progress.update(task, description="✅ Components initialized")
            progress.remove_task(task)

            # Calculate production capacities
            task = progress.add_task("Calculating production capacities...", total=None)
            capacities = capacity_calc.calculate_all_capacities(operators)
            progress.update(task, description=f"✅ Calculated {len(capacities)} capacities")
            progress.remove_task(task)

            # Calculate demand
            task = progress.add_task("Calculating resource demand...", total=None)
            demand = demand_calc.calculate_all_demand(operators)
            progress.update(task, description=f"✅ Calculated demand for {len(demand)} operators")
            progress.remove_task(task)

            # Calibrate so world supply matches final demand plus production inputs;
            # demand from here on includes the inputs each operator consumes
            capacities, demand = calibrate_with_input_demand(
                capacities, rules_engine, demand, config.supply_demand_ratio
            )

            # Calculate supply (from capacities)
            task = progress.add_task("Calculating resource supply...", total=None)
            supply = _calculate_supply_from_capacities(capacities, operators, rules_engine)
            progress.update(task, description=f"✅ Calculated supply for {len(supply)} operators")
            progress.remove_task(task)

            # Calculate prices
            task = progress.add_task("Calculating market prices...", total=None)
            prices = price_calc.calculate_prices(operators, supply, demand)
            progress.update(task, description=f"✅ Calculated prices for {len(prices)} operators")
            progress.remove_task(task)

            # Solve trade flows
            task = progress.add_task("Solving trade network...", total=None)
            trade_links = trade_network.solve_trade_flows(supply, demand, prices)
            progress.update(task, description=f"✅ Generated {len(trade_links)} trade links")
            progress.remove_task(task)

        # Write outputs
        console.print("\n📝 Writing output files...")
        _write_outputs(output_dir, operators, capacities, demand, supply, prices, trade_links)

        # Generate report
        console.print("📊 Generating analysis report...")
        report_gen = ReportGenerator(operators, trade_links, capacities, prices, supply, demand)
        report = report_gen.generate_full_report()
        report_file = output_dir / "economic_analysis.md"
        report_file.write_text(report, encoding="utf-8")

        # Display summary
        elapsed_time = time.time() - start_time
        _display_summary(operators, trade_links, capacities, elapsed_time)

        console.print("\n✅ [bold green]Simulation completed successfully![/bold green]")
        console.print(f"📁 Results written to: [bold]{output_dir}[/bold]")

    except Exception as e:
        console.print(f"❌ [red]Simulation failed: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def validate(
    input_paths: list[Path] = typer.Option(..., "--input", "-i", help="GeoJSON files to validate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose validation output"),
):
    """Validate GeoJSON input files without running full simulation."""
    console.print("[blue]🔍 Validating GeoJSON files...[/blue]")

    loader = GeoJSONLoader(strict=True)
    failed = 0

    for path in input_paths:
        try:
            operators = loader.load_operators([path])
            console.print(f"✅ {path.name}: [green]{len(operators)} valid operators[/green]")

            if verbose and operators:
                # Show some sample data
                sample = operators[0]
                console.print(
                    f"   Sample: {sample.name} ({sample.tech!s}, pop: {sample.population})"
                )

        except Exception as e:
            failed += 1
            console.print(f"❌ {path.name}: [red]{e}[/red]")

    # Reason: check every file first so one run reports all problems, then fail the command.
    if failed:
        console.print(f"[red]{failed} of {len(input_paths)} file(s) failed validation[/red]")
        raise typer.Exit(1)


@app.command()
def config_template(
    output_file: Path = typer.Option(
        Path("config_template.yaml"),
        "--output",
        "-o",
        help="Output file for configuration template",
    ),
):
    """Generate a configuration template file."""
    console.print("📝 Generating configuration template...")

    # Create template configuration
    template = {
        "simulation": {
            "max_trade_neighbors": 8,
            "max_trade_radius_km": 800,
            "min_trade_quantity": 0.5,
            "transport_cost_per_km": 0.02,
            "supply_demand_ratio": 1.0,
            "scarcity_multiplier": True,
            "price_elasticity": 1.5,
            "seed": None,
            "strict_validation": True,
        },
        "dynamics": {
            # Optional Minsky stock/flow layer (see `simulate` command)
            "minsky_root": minsky_root(),
            "n_steps": 50,
            "include_trade": False,
            "resources": None,
        },
        "resources": [
            {
                "resource_id": "wood",
                "name": "Wood",
                "tier": 0,
                "tech_min": "tribal",
                "base_price": 1.0,
                "transportable": True,
                "perishable": False,
            },
            {
                "resource_id": "iron-ore",
                "name": "Iron Ore",
                "tier": 0,
                "tech_min": "medieval",
                "base_price": 3.0,
                "transportable": True,
                "perishable": False,
            },
        ],
        "rules": [
            {
                "rule_id": "toolmaking",
                "name": "Tool Making",
                "tech_min": "tribal",
                "inputs": {"wood": 2.0, "stone": 1.0},
                "outputs": {"tools": 1.0},
                "capacity_driver": "craftsmanship",
                "labor_required": 3.0,
            }
        ],
        "demand_profiles": [
            {"tech": "tribal", "per_capita": {"wood": 0.5, "tools": 0.1, "food": 2.0}}
        ],
    }

    with open(output_file, "w") as f:
        yaml.safe_dump(template, f, indent=2, default_flow_style=False)

    console.print(f"✅ Template written to: [bold]{output_file}[/bold]")


def _write_outputs(output_dir: Path, operators, capacities, demand, supply, prices, trade_links):
    """Write all output files."""
    # Operators
    operators_file = output_dir / "operators.jsonl"
    with open(operators_file, "w") as f:
        f.writelines(op.model_dump_json() + "\n" for op in operators)

    # Capacities
    capacities_file = output_dir / "capacities.jsonl"
    with open(capacities_file, "w") as f:
        f.writelines(cap.model_dump_json() + "\n" for cap in capacities)

    # Trade links
    trade_file = output_dir / "trade_links.jsonl"
    with open(trade_file, "w") as f:
        f.writelines(link.model_dump_json() + "\n" for link in trade_links)

    # Demand (JSON)
    demand_file = output_dir / "demand.json"
    demand_serializable = {
        op_id: {res_id: float(qty) for res_id, qty in resources.items()}
        for op_id, resources in demand.items()
    }
    with open(demand_file, "w") as f:
        json.dump(demand_serializable, f, indent=2)

    # Supply (JSON)
    supply_file = output_dir / "supply.json"
    supply_serializable = {
        op_id: {res_id: float(qty) for res_id, qty in resources.items()}
        for op_id, resources in supply.items()
    }
    with open(supply_file, "w") as f:
        json.dump(supply_serializable, f, indent=2)

    # Prices (JSON)
    prices_file = output_dir / "prices.json"
    prices_serializable = {
        op_id: {res_id: float(price) for res_id, price in resources.items()}
        for op_id, resources in prices.items()
    }
    with open(prices_file, "w") as f:
        json.dump(prices_serializable, f, indent=2)


def _display_summary(operators, trade_links, capacities, elapsed_time):
    """Display execution summary."""
    table = Table(title="Simulation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Total Operators", str(len(operators)))
    table.add_row("Production Capacities", str(len(capacities)))
    table.add_row("Trade Links", str(len(trade_links)))
    table.add_row("Execution Time", f"{elapsed_time:.2f}s")

    # Tech level breakdown
    tech_counts = {}
    for op in operators:
        tech_counts[op.tech] = tech_counts.get(op.tech, 0) + 1

    for tech, count in tech_counts.items():
        table.add_row(f"  {str(tech).title()} Era", str(count))

    console.print(table)


if __name__ == "__main__":
    app()
