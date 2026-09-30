"""Render FinancialAnalysis into markdown profiles + Godley transactions matrix."""

from collections import Counter
from typing import List

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


def _godley_matrix(analysis: FinancialAnalysis) -> List[str]:
    """Render a Godley-style transactions matrix (sectors as columns, sum to zero)."""
    m = analysis.material
    k = analysis.karmic
    w, c, t, e = m.wages, m.consumption, m.trade_balance, k.utai_extraction
    # Household balance = wages - consumption - debt_servicing_share
    # Producers balance = GDP - wages + consumption_from_households + trade
    # Utaia = +extraction; RoW = -trade
    lines = [
        "",
        "## Godley Transactions Matrix",
        "",
        "| Transaction | Households | Producers | Utaia | Rest-of-World | Σ |",
        "|---|---|---|---|---|---|",
        f"| Consumption | {-c:,.0f} | {c:,.0f} | | | 0 |",
        f"| Wages | {w:,.0f} | {-w:,.0f} | | | 0 |",
        f"| Net trade | | {t:,.0f} | | {-t:,.0f} | 0 |",
        f"| Debt servicing | {-e:,.0f} | | {e:,.0f} | | 0 |",
        f"| **Sector balance** | **{w - c - e:,.0f}** | **{m.gdp - w + c + t:,.0f}** | **{e:,.0f}** | **{-t:,.0f}** | **0** |",
        "",
        "_Columns sum to zero (stock-flow consistent). Positive = inflow, negative = outflow._",
    ]
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
