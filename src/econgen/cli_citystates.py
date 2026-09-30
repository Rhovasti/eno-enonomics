"""Citystate CLI commands: profiles, dynamics, chronicles, financial, governance."""

import json
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .cli_common import app, console
from .citystates import load_citystates
from .paths import DEFAULT_CITYSTATES_DIR as DEFAULT_CITYSTATES_PATH
from .paths import ENV_CITYSTATES_DIR
from .citystates.economy import city_potential_supply_demand, city_supply_demand, make_economy
from .citystates.market import compute_market_prices
from .citystates.profiles import (
    ProfileConfig,
    compute_citystate_profile,
    render_profile,
)

DEFAULT_CITYSTATES_DIR = Path(DEFAULT_CITYSTATES_PATH)


def _write_citystate_index(output_dir: Path, profiles: list) -> None:
    """Write a markdown index table of all citystate profiles, sorted by trade balance."""
    rows = sorted(profiles, key=lambda p: p.trade_balance)
    lines = [
        "# Citystate Economic Profiles (cycle 998)",
        "",
        "| Citystate | State | Valley | Pop | Tech | Trade balance | Specialization |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in rows:
        flow = "exporter" if p.trade_balance < 0 else "importer"
        lines.append(
            f"| {p.name} | {p.temporal_state} | {p.valley} | {p.population:,} | "
            f"{p.tech} | {p.trade_balance:+.0f} ({flow}) | {', '.join(p.specialization)} |"
        )
    (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.command()
def citystate_sim(
    citystates_dir: Path = typer.Option(
        DEFAULT_CITYSTATES_DIR,
        "--citystates-dir",
        envvar=ENV_CITYSTATES_DIR,
        help="Directory of citystate .md profiles",
    ),
    output_dir: Path = typer.Option(
        Path("out/citystates"), "--output", "-o", help="Output directory for profiles"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Only profile the first N citystates (for testing)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Compute cycle-998 economic profiles for all citystates (Phase 2)."""
    start_time = time.time()
    console.print(
        Panel.fit(
            "[bold blue]Citystate Economic Profiles — cycle 998[/bold blue]", border_style="blue"
        )
    )
    try:
        specs = load_citystates(citystates_dir)
        if limit is not None:
            specs = specs[:limit]
        console.print(f"📍 Loaded {len(specs)} citystates from {citystates_dir.name}")

        taxonomy, rules, demand_calc = make_economy()
        console.print("🌐 Computing world market prices across all citystates...")
        market_prices = compute_market_prices(specs, taxonomy, rules, demand_calc)

        output_dir.mkdir(parents=True, exist_ok=True)
        config = ProfileConfig()
        profiles = []
        for spec in specs:
            supply, demand = city_supply_demand(spec, taxonomy, rules, demand_calc)
            profile = compute_citystate_profile(
                spec, supply, demand, market_prices, taxonomy, config
            )
            (output_dir / f"{profile.name}.md").write_text(
                render_profile(profile), encoding="utf-8"
            )
            (output_dir / f"{profile.name}.json").write_text(profile.model_dump_json(indent=2))
            profiles.append(profile)

        _write_citystate_index(output_dir, profiles)

        elapsed = time.time() - start_time
        exporters = sum(1 for p in profiles if p.trade_balance < 0)
        console.print(
            f"✅ Profiled {len(profiles)} citystates in {elapsed:.1f}s — "
            f"{exporters} net exporters, {len(profiles) - exporters} net importers"
        )
        console.print(f"📁 Profiles + index written to: [bold]{output_dir}[/bold]")
    except Exception as e:
        console.print(f"❌ [red]{e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def citystate_dynamic(
    citystates_dir: Path = typer.Option(
        DEFAULT_CITYSTATES_DIR,
        "--citystates-dir",
        envvar=ENV_CITYSTATES_DIR,
        help="Directory of citystate .md profiles",
    ),
    output_dir: Path = typer.Option(
        Path("out/citystates_dynamic"),
        "--output",
        "-o",
        help="Output directory for dynamic histories",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Only simulate the first N citystates (for testing)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run per-city dynamic simulation (growth + tech + depletion), founding -> 998."""
    from .citystates.simulator import CitystateSimConfig, save_history, simulate_city
    from .dynamics.client import MinskyClient

    start_time = time.time()
    console.print(
        Panel.fit(
            "[bold blue]Citystate Dynamic Histories — founding to cycle 998[/bold blue]\n"
            "[dim]growth + tech progression + depletion[/dim]",
            border_style="blue",
        )
    )
    try:
        specs = load_citystates(citystates_dir)
        if limit is not None:
            specs = specs[:limit]
        taxonomy, rules, demand_calc = make_economy()
        config = CitystateSimConfig()
        client = MinskyClient()
        output_dir.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task(f"Simulating {len(specs)} citystates...", total=len(specs))
            for spec in specs:
                supply, demand, unlock_rank = city_potential_supply_demand(
                    spec, taxonomy, rules, demand_calc
                )
                history = simulate_city(
                    client, spec, supply, demand, taxonomy, rules, config, unlock_rank
                )
                save_history(history, output_dir)
                progress.advance(task)

        elapsed = time.time() - start_time
        console.print(
            f"✅ Wrote {len(specs)} dynamic histories to [bold]{output_dir}[/bold] "
            f"in {elapsed:.0f}s"
        )
    except Exception as e:
        console.print(f"❌ [red]{e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def citystate_chronicle(
    citystates_dir: Path = typer.Option(
        DEFAULT_CITYSTATES_DIR,
        "--citystates-dir",
        envvar=ENV_CITYSTATES_DIR,
        help="Directory of citystate .md profiles (for temporal_state/valley)",
    ),
    histories_dir: Path = typer.Option(
        Path("out/citystates_dynamic"),
        "--histories-dir",
        help="Directory of dynamic history JSONs (from citystate-dynamic)",
    ),
    output_dir: Path = typer.Option(
        Path("out/citystates_chronicles"), "--output", "-o", help="Output directory for chronicles"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Render dynamic histories into narrative per-city chronicles."""
    from .citystates.chronicles import render_chronicle

    console.print(
        Panel.fit(
            "[bold blue]Citystate Chronicles[/bold blue]\n"
            "[dim]narrative economic histories, founding to cycle 998[/dim]",
            border_style="blue",
        )
    )
    try:
        specs = {s.name: s for s in load_citystates(citystates_dir)}
        taxonomy, rules, _ = make_economy()
        extractive: set = set()
        for rule in rules.rules.values():
            cd = rule.capacity_driver
            if cd == "mining_potential" or (cd and cd.endswith("_deposit")):
                extractive.update(rule.outputs)
        output_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for hist_file in sorted(histories_dir.glob("*.json")):
            history = json.loads(hist_file.read_text(encoding="utf-8"))
            spec = specs.get(history.get("name"))
            if spec is None:
                continue
            chronicle = render_chronicle(history, spec, extractive)
            (output_dir / f"{history['name']}.md").write_text(chronicle, encoding="utf-8")
            count += 1
        console.print(f"✅ Wrote {count} chronicles to [bold]{output_dir}[/bold]")
    except Exception as e:
        console.print(f"❌ [red]{e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def citystate_financial(
    citystates_dir: Path = typer.Option(
        DEFAULT_CITYSTATES_DIR,
        "--citystates-dir",
        envvar=ENV_CITYSTATES_DIR,
        help="Directory of citystate .md profiles",
    ),
    output_dir: Path = typer.Option(
        Path("out/citystates_financial"),
        "--output",
        "-o",
        help="Output directory for financial analyses",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Only analyze the first N citystates (for testing)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Compute SFC financial analyses (material + karmic-debt) for all citystates."""
    from .financial.analysis import compute_financial_analysis, compute_utai_aggregate
    from .financial.narrative import render_financial_profile, render_utai_profile

    start_time = time.time()
    console.print(
        Panel.fit(
            "[bold blue]Citystate Financial Analysis — SFC + Karmic Debt[/bold blue]\n"
            "[dim]material value-unit economy + Utaia debt extraction[/dim]",
            border_style="blue",
        )
    )
    try:
        specs = load_citystates(citystates_dir)
        if limit is not None:
            specs = specs[:limit]
        taxonomy, rules, demand_calc = make_economy()
        console.print("🌐 Computing world market prices...")
        market_prices = compute_market_prices(specs, taxonomy, rules, demand_calc)

        output_dir.mkdir(parents=True, exist_ok=True)
        analyses = []
        for spec in specs:
            supply, demand = city_supply_demand(spec, taxonomy, rules, demand_calc)
            analysis = compute_financial_analysis(spec, supply, demand, market_prices)
            (output_dir / f"{spec.name}.md").write_text(
                render_financial_profile(analysis), encoding="utf-8"
            )
            (output_dir / f"{spec.name}.json").write_text(
                analysis.model_dump_json(indent=2), encoding="utf-8"
            )
            analyses.append(analysis)

        # Utaia aggregate.
        portfolio = compute_utai_aggregate(analyses)
        (output_dir / "utai_dominion.md").write_text(
            render_utai_profile(portfolio, analyses), encoding="utf-8"
        )
        (output_dir / "utai_dominion.json").write_text(
            portfolio.model_dump_json(indent=2), encoding="utf-8"
        )

        # Index.
        dist = Counter(a.financial_health for a in analyses)
        lines = [
            "# Citystate Financial Analysis Index (cycle 998)",
            "",
            "| Citystate | State | Health | Score | GDP | Karmic Debt | Credit |",
            "|---|---|---|---|---|---|---|",
        ]
        for a in sorted(analyses, key=lambda x: x.health_score):
            lines.append(
                f"| {a.name} | {a.temporal_state} | {a.financial_health} | "
                f"{a.health_score:.0f} | {a.material.gdp:,.0f} | "
                f"{a.karmic.karmic_debt:,.0f} | {a.karmic.credit_standing} |"
            )
        (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        elapsed = time.time() - start_time
        console.print(
            f"✅ Analyzed {len(analyses)} citystates in {elapsed:.1f}s — "
            f"{dist.get('prosperous', 0)} prosperous, {dist.get('stable', 0)} stable, "
            f"{dist.get('vulnerable', 0)} vulnerable, {dist.get('crisis', 0)} crisis"
        )
        console.print(
            f"🏛️ Utaia portfolio: {portfolio.total_debt:,.0f} karmic debt, "
            f"{portfolio.total_extraction:,.0f}/cycle extraction "
            f"({portfolio.extraction_as_pct_of_regional_gdp:.2f}% of regional GDP)"
        )
        console.print(f"📁 Profiles + Utaia dominion + index at [bold]{output_dir}[/bold]")
    except Exception as e:
        console.print(f"❌ [red]{e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def citystate_governance(
    citystates_dir: Path = typer.Option(
        DEFAULT_CITYSTATES_DIR,
        "--citystates-dir",
        envvar=ENV_CITYSTATES_DIR,
        help="Directory of citystate .md profiles",
    ),
    output_dir: Path = typer.Option(
        Path("out/citystates_governance"),
        "--output",
        "-o",
        help="Output directory for governance assignments",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Only assign the first N citystates (for testing)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Assign governance types to all citystates based on economic/cultural data."""
    from .citystates.governance import (
        assign_governance,
        assign_initial_governance,
        compute_progression,
        create_dam_settlement,
    )
    from .citystates.roots import assign_roots
    from .financial.analysis import compute_financial_analysis

    console.print(
        Panel.fit(
            "[bold blue]Citystate Governance Evolution[/bold blue]\n"
            "[dim]Roots → Initial (founding) → Settled (998) + progression[/dim]",
            border_style="blue",
        )
    )
    try:
        specs = load_citystates(citystates_dir)
        if limit is not None:
            specs = specs[:limit]
        specs.append(create_dam_settlement())
        taxonomy, rules, demand_calc = make_economy()
        console.print("🌐 Computing market prices + economic profiles...")
        market_prices = compute_market_prices(specs, taxonomy, rules, demand_calc)

        economic_data = {}
        for spec in specs:
            supply, demand = city_supply_demand(spec, taxonomy, rules, demand_calc)
            analysis = compute_financial_analysis(spec, supply, demand, market_prices)
            economic_data[spec.name] = {
                "gdp": analysis.material.gdp,
                "trade_balance": analysis.material.trade_balance,
                "financial_health": analysis.financial_health,
            }

        console.print(f"🏛️ Assigning governance evolution to {len(specs)} citystates...")
        settled_assignments = assign_governance(specs, economic_data)
        settled = {a.name: a.gov_type for a in settled_assignments}
        settled_notes = {a.name: a for a in settled_assignments}

        roots = assign_roots(specs)
        initial = assign_initial_governance(specs, roots, settled)

        output_dir.mkdir(parents=True, exist_ok=True)
        all_types = set()
        for spec in specs:
            name = spec.name
            root = roots.get(name, "unknown")
            init_gov = initial.get(name, "unknown")
            set_gov = settled.get(name, "unknown")
            prog = compute_progression(init_gov, set_gov)
            all_types.add(init_gov)
            sa = settled_notes.get(name)
            record = {
                "name": name,
                "root": root,
                "initial_governance": init_gov,
                "settled_governance": set_gov,
                "progression": prog,
                "category": sa.category if sa else "",
                "eno_note": sa.eno_note if sa else "",
                "rationale": sa.rationale if sa else [],
                "hard_coded": sa.hard_coded if sa else False,
            }
            (output_dir / f"{name}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            all_types.add(set_gov)

        # Index with all three layers.
        lines = [
            "# Citystate Governance Evolution (Roots → Initial → Settled)",
            "",
            "| Citystate | Root | Initial (founding) | Settled (998) | Progression |",
            "|---|---|---|---|---|",
        ]
        for spec in specs:
            name = spec.name
            lines.append(
                f"| {name} | {roots.get(name, '?')} | {initial.get(name, '?')} | "
                f"{settled.get(name, '?')} | "
                f"{compute_progression(initial.get(name, ''), settled.get(name, ''))} |"
            )
        (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        init_dist = Counter(initial.get(s.name) for s in specs)
        settled_dist = Counter(settled.get(s.name) for s in specs)
        prog_dist = Counter(
            compute_progression(initial.get(s.name, ""), settled.get(s.name, "")) for s in specs
        )
        console.print(f"\n✅ Governance evolution for {len(specs)} citystates:")
        console.print(
            f"   Initial types: {len(init_dist)} | Settled types: {len(settled_dist)} "
            f"| Total unique: {len(all_types)}"
        )
        console.print(f"   Progression: {dict(prog_dist.most_common())}")
        console.print(f"📁 Trajectories + index at [bold]{output_dir}[/bold]")
    except Exception as e:
        console.print(f"❌ [red]{e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
