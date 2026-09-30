"""Combined financial analysis: material SFC + karmic-debt + health score + Utaia aggregate."""

from typing import Dict, List

from pydantic import BaseModel

from ..citystates.economy import _tech_for
from ..citystates.parser import CitystateSpec
from .karmic import KarmicSFC, compute_karmic_sfc
from .sfc import MaterialSFC, compute_material_sfc


class FinancialAnalysis(BaseModel):
    """Full financial analysis for one citystate (material + karmic)."""

    name: str
    temporal_state: str
    valley: str
    population: int
    tech: str
    founded_cycle: int

    material: MaterialSFC
    karmic: KarmicSFC

    health_score: float  # 0-100
    financial_health: str  # prosperous / stable / vulnerable / crisis


class UtaiaPortfolio(BaseModel):
    """Utaia's aggregated financial position across all citystates."""

    total_debt: float
    total_extraction: float
    total_tokens: float  # forgiveness tokens in circulation
    total_outstanding_debt: float  # unforgiven debt under Utaia's management
    debtor_count: int
    most_indebted: List[str]
    extraction_as_pct_of_regional_gdp: float


def compute_financial_analysis(
    spec: CitystateSpec,
    supply: Dict,
    demand: Dict,
    market_prices: Dict[str, float],
) -> FinancialAnalysis:
    """Compute the combined financial analysis for one citystate."""
    tech = _tech_for(spec)
    material = compute_material_sfc(spec, supply, demand, market_prices, tech)
    karmic = compute_karmic_sfc(spec, material.gdp)

    # Health score: base 50 + savings bonus - debt penalty.
    score = 50.0
    gdp = max(material.gdp, 1.0)
    score += min(material.savings / gdp * 100.0, 20.0)  # up to +20 for high savings
    score -= karmic.debt_to_gdp * 100.0  # -1 per 1% debt-to-GDP
    if material.trade_balance > 0:
        score -= min(material.trade_balance / gdp * 10.0, 10.0)  # trade deficit penalty
    score = max(0.0, min(100.0, score))

    if score >= 70:
        health = "prosperous"
    elif score >= 50:
        health = "stable"
    elif score >= 30:
        health = "vulnerable"
    else:
        health = "crisis"

    return FinancialAnalysis(
        name=spec.name,
        temporal_state=spec.temporal_state,
        valley=spec.valley,
        population=spec.population,
        tech=tech,
        founded_cycle=spec.founded_cycle,
        material=material,
        karmic=karmic,
        health_score=score,
        financial_health=health,
    )


def compute_utai_aggregate(analyses: List[FinancialAnalysis]) -> UtaiaPortfolio:
    """Aggregate all citystates' karmic debt into Utaia's portfolio."""
    total_debt = sum(a.karmic.karmic_debt for a in analyses)
    total_tokens = sum(a.karmic.forgiveness_tokens for a in analyses)
    total_outstanding = sum(a.karmic.outstanding_debt for a in analyses)
    total_extraction = sum(a.karmic.utai_extraction for a in analyses)
    regional_gdp = sum(a.material.gdp for a in analyses)
    debtors = sorted(analyses, key=lambda a: -a.karmic.karmic_debt)
    return UtaiaPortfolio(
        total_debt=total_debt,
        total_extraction=total_extraction,
        total_tokens=total_tokens,
        total_outstanding_debt=total_outstanding,
        debtor_count=sum(1 for a in analyses if a.karmic.karmic_debt > 0),
        most_indebted=[a.name for a in debtors[:5]],
        extraction_as_pct_of_regional_gdp=total_extraction / regional_gdp * 100
        if regional_gdp
        else 0,
    )


__all__ = [
    "FinancialAnalysis",
    "UtaiaPortfolio",
    "compute_financial_analysis",
    "compute_utai_aggregate",
]
