"""Render FinancialAnalysis into markdown profiles + Godley transactions matrix."""

from collections import Counter
from typing import Dict, List, Tuple

from .analysis import FinancialAnalysis, UtaiaPortfolio
from .parameters import OFFENSE_TIERS


def render_financial_profile(analysis: FinancialAnalysis) -> str:
    """Render a citystate's financial analysis as a markdown profile."""
    m = analysis.material
    k = analysis.karmic
    lines = [
        f"# Financial Profile: {analysis.name}",
        "",
        f"- **State**: {analysis.temporal_state} · **Valley**: {analysis.valley} · "
        f"**Pop**: {analysis.population:,} · **Tech**: {analysis.tech}",
        f"- **Financial Health**: {analysis.financial_health.title()} (score: {analysis.health_score:.0f}/100)",
        "",
        "## Material Economy (value units)",
        "",
        f"- **GDP**: {m.gdp:,.0f} | **Per capita income**: {m.per_capita_income:.1f}",
        f"- **Wages**: {m.wages:,.0f} ({m.wages / max(m.gdp, 1) * 100:.0f}% of GDP) | "
        f"**Producer surplus**: {m.producer_surplus:,.0f}",
        f"- **Consumption**: {m.consumption:,.0f} | **Savings**: {m.savings:,.0f}",
        f"- **Household wealth**: {m.household_wealth:,.0f} ({m.per_capita_wealth:.1f}/cap)",
        f"- **Trade balance**: {m.trade_balance:+,.0f} ({'deficit' if m.trade_balance > 0 else 'surplus'})",
        f"- **Alchemists' Guild value added**: {m.alchemical_value_added:,.0f} "
        f"({m.alchemical_value_added / max(m.gdp, 1) * 100:.1f}% of GDP — "
        f"components {m.alchemical_split['component']:,.0f}, "
        f"elements {m.alchemical_split['element']:,.0f}, "
        f"stuffs {m.alchemical_split['stuff']:,.0f})",
        "",
        "### Income by Labor Tier",
        "",
        "| Tier | Total Income |",
        "|---|---|",
    ]
    for tier, income in sorted(m.income_by_tier.items(), key=lambda x: -x[1]):
        if income > 0:
            lines.append(f"| {tier} | {income:,.0f} |")

    # --- Karmic Debt section ---
    lines.extend(
        [
            "",
            "## Karmic Debt (spiritual finance)",
            "",
            f"- **Total karmic debt**: {k.karmic_debt:,.0f} (property-offense units)",
            f"- **Debt-to-GDP ratio**: {k.debt_to_gdp * 100:.1f}%",
            f"- **Dominant offense tier**: {k.dominant_tier}",
            f"- **Credit standing**: {k.credit_standing}",
            f"- **Forgiveness tokens generated**: {k.forgiveness_tokens:,.0f} (tradeable currency)",
            f"- **Outstanding debt (Utaia-extractable)**: {k.outstanding_debt:,.0f}",
            f"- **Annual Utaia extraction**: {k.utai_extraction:,.0f}",
            "",
            "### Offense Breakdown by Tier",
            "",
            "| Tier | Offenses | Weighted Debt | Weight |",
            "|---|---|---|---|",
        ]
    )
    for name, weight in OFFENSE_TIERS:
        count = k.offenses_by_tier.get(name, 0)
        weighted = count * weight
        if count > 0:
            lines.append(f"| {name} | {count:,.1f} | {weighted:,.0f} | {weight}x |")

    # --- Godley Transactions Matrix ---
    lines.extend(_godley_matrix(analysis))

    lines.extend(
        [
            "",
            f"_{analysis.name} is a **{analysis.financial_health}** economy (score "
            f"{analysis.health_score:.0f}/100) with {k.credit_standing} karmic debt. "
            f"{'Utaia extracts ' + format(k.utai_extraction, ',.0f') + '/cycle.' if k.utai_extraction > 0 else ''}_",
            "",
        ]
    )
    return "\n".join(lines)


def _godley_transactions(analysis: FinancialAnalysis) -> List[Tuple[str, Dict[str, float]]]:
    """The Godley-style transactions rows: (label, {sector: signed flow}).

    Sectors: Households, Producers, Alchemists' Guild, Utaia, Rest-of-World.
    Each row's cells sum to zero. The Guild column balances exactly by
    construction (value added - guild wages - dividends = 0).
    """
    m = analysis.material
    k = analysis.karmic
    w, c, t, e = m.wages, m.consumption, m.trade_balance, k.utai_extraction
    va, w_a, c_a, d_a = (
        m.alchemical_value_added,
        m.guild_wages,
        m.guild_consumption,
        m.guild_surplus,
    )
    return [
        ("Consumption", {"Households": -(c - c_a), "Producers": c - c_a}),
        ("Alchemical consumption", {"Households": -c_a, "Guild": c_a}),
        ("Wages", {"Households": w - w_a, "Producers": -(w - w_a)}),
        ("Alchemical wages", {"Households": w_a, "Guild": -w_a}),
        (
            "Alchemical input sales",
            {"Producers": -(va - c_a), "Guild": va - c_a},
        ),
        ("Guild dividends", {"Producers": d_a, "Guild": -d_a}),
        ("Net trade", {"Producers": t, "Rest-of-World": -t}),
        ("Debt servicing", {"Households": -e, "Utaia": e}),
    ]


SECTORS = ["Households", "Producers", "Guild", "Utaia", "Rest-of-World"]


def _godley_matrix(analysis: FinancialAnalysis) -> List[str]:
    """Render a Godley-style transactions matrix (each row sums to zero)."""
    rows = _godley_transactions(analysis)
    lines = [
        "",
        "## Godley Transactions Matrix",
        "",
        "| Transaction | " + " | ".join(SECTORS) + " | Σ |",
        "|---|" + "---|" * (len(SECTORS) + 1),
    ]
    for label, cells in rows:
        values = [cells.get(sector) for sector in SECTORS]
        rendered = " | ".join(f"{v:,.0f}" if v is not None else "" for v in values)
        lines.append(f"| {label} | {rendered} | 0 |")

    balances: Dict[str, float] = {sector: 0.0 for sector in SECTORS}
    for _, cells in rows:
        for sector, value in cells.items():
            balances[sector] += value
    balance_cells = " | ".join(f"**{balances[s]:,.0f}**" for s in SECTORS)
    lines.append(f"| **Sector balance** | {balance_cells} | |")
    lines.extend(
        [
            "",
            "_Each transaction row sums to zero; the Guild column balances exactly "
            "(value added − guild wages − dividends). Positive = inflow._",
        ]
    )
    return lines


def render_utai_profile(portfolio: UtaiaPortfolio, analyses: List[FinancialAnalysis]) -> str:
    """Render Utaia's aggregated financial dominion."""
    lines = [
        "# Financial Profile: Citadel of Utaia (Dominion of Worth)",
        "",
        "Utaia is the financial hub of Eno — a parasitic debt-market monopolist whose",
        "portfolio aggregates karmic-debt instruments from across all citystates.",
        "",
        "## Aggregate Portfolio",
        "",
        f"- **Total karmic debt under management**: {portfolio.total_debt:,.0f}",
        f"- **Forgiveness tokens in circulation**: {portfolio.total_tokens:,.0f}",
        f"- **Outstanding (unforgiven) debt**: {portfolio.total_outstanding_debt:,.0f}",
        f"- **Annual extraction (debt servicing)**: {portfolio.total_extraction:,.0f}",
        f"- **Extraction as % of regional GDP**: {portfolio.extraction_as_pct_of_regional_gdp:.2f}%",
        f"- **Debtor citystates**: {portfolio.debtor_count}",
        f"- **Most indebted**: {', '.join(portfolio.most_indebted)}",
        "",
        "## Regional Financial Health Distribution",
        "",
    ]
    dist = Counter(a.financial_health for a in analyses)
    for state in ["prosperous", "stable", "vulnerable", "crisis"]:
        lines.append(f"- **{state.title()}**: {dist.get(state, 0)} citystates")
    lines.append("")
    return "\n".join(lines)


__all__ = ["render_financial_profile", "render_utai_profile"]
