"""``simulate`` CLI command: Minsky stock/flow dynamics over a static snapshot."""

import time
import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.panel import Panel

from .cli_common import (
    _compute_supply_and_demand,
    _resolve_dynamics_config,
    app,
    console,
)
from .trade import TradeNetwork
from .util import set_seed
from .dynamics import (
    MinskyClient,
    MinskyUnavailable,
    build_dynamics_input,
    write_outputs,
)
from .dynamics.runner import simulate as run_dynamics_simulation


@app.command()
def simulate(
    input_paths: List[Path] = typer.Option(
        ...,
        "--input",
        "-i",
        help="GeoJSON input files containing city/operator data",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration YAML file (uses defaults if not provided)",
        exists=True,
    ),
    output_dir: Path = typer.Option(
        Path("out/econ"), "--output", "-o", help="Output directory for results"
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", "-s", help="Random seed for deterministic results"
    ),
    steps: Optional[int] = typer.Option(
        None, "--steps", help="Number of integration steps (overrides dynamics.n_steps)"
    ),
    resource: Optional[str] = typer.Option(
        None, "--resource", help="Restrict simulation to a single resource id"
    ),
    trade: bool = typer.Option(
        False, "--trade", help="Wire inter-city diffusion trade (recommended with --resource)"
    ),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Strict validation mode"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """Simulate the economy forward in time via Minsky (dynamic layer).

    Builds a stock/flow model from the static economic snapshot (production
    minus consumption per city/resource) and integrates it, writing time-series
    plus a reusable .mky model file.
    """
    start_time = time.time()
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(
        Panel.fit(
            "[bold blue]Enonomics × Minsky — Dynamic Simulation[/bold blue]\n"
            "[dim]Stock/flow integration of a static economic snapshot[/dim]",
            border_style="blue",
        )
    )

    try:
        if seed is not None:
            set_seed(seed)

        (
            operators,
            supply,
            demand,
            dynamics_config,
            sim_config,
            taxonomy,
            rules_engine,
        ) = _compute_supply_and_demand(input_paths, config_path, seed, strict)
        if trade:
            dynamics_config = dynamics_config.model_copy(update={"include_trade": True})
        dynamics_config = _resolve_dynamics_config(dynamics_config, steps, seed, resource)
        if dynamics_config.include_trade and dynamics_config.resources is None:
            console.print(
                "⚠️  [yellow]Trade across ALL resources builds a very large model; "
                "consider also passing --resource.[/yellow]"
            )
        output_dir.mkdir(parents=True, exist_ok=True)

        trade_network = (
            TradeNetwork(operators, sim_config) if dynamics_config.include_trade else None
        )
        dynamics_input = build_dynamics_input(
            operators, supply, demand, dynamics_config, trade_network, taxonomy, rules_engine
        )
        if not dynamics_input.stocks:
            console.print("⚠️  [yellow]No stocks to simulate (no supply/demand matched).[/yellow]")
            raise typer.Exit(1)

        edge_note = (
            f", {len(dynamics_input.trade_edges)} trade edges" if dynamics_input.trade_edges else ""
        )
        console.print(
            f"🧱 Building {len(dynamics_input.stocks)} stocks{edge_note}, "
            f"integrating {dynamics_config.n_steps} steps..."
        )
        client = MinskyClient(dynamics_config.minsky_root)
        result = run_dynamics_simulation(client, dynamics_input)
        write_outputs(output_dir, dynamics_input, result, client)

        elapsed = time.time() - start_time
        console.print(f"✅ [bold green]Dynamic simulation completed in {elapsed:.2f}s[/bold green]")
        console.print(f"📁 Results written to: [bold]{output_dir}[/bold]")
        console.print(f"🧮 Model: {result.model_path}")
        first_name = next(iter(result.series), None)
        if first_name is not None:
            series = result.series[first_name]
            console.print(
                f"📈 Sample '{first_name}': "
                f"{series[0]:.3f} → {series[-1]:.3f} over {len(series)} steps"
            )
    except MinskyUnavailable as e:
        console.print(f"❌ [red]{e}[/red]")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"❌ [red]Dynamic simulation failed: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
