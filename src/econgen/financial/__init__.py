"""Financial analysis layer for citystates — SFC (material + karmic-debt)."""

from .analysis import (
    FinancialAnalysis,
    UtaiaPortfolio,
    compute_financial_analysis,
    compute_utai_aggregate,
)
from .karmic import KarmicSFC, compute_karmic_sfc
from .narrative import render_financial_profile, render_utai_profile
from .parameters import FINANCIAL_PARAMS, LABOR_TIERS, TIER_DISTRIBUTION
from .sfc import MaterialSFC, compute_material_sfc

__all__ = [
    "FINANCIAL_PARAMS",
    "LABOR_TIERS",
    "TIER_DISTRIBUTION",
    "FinancialAnalysis",
    "KarmicSFC",
    "MaterialSFC",
    "UtaiaPortfolio",
    "compute_financial_analysis",
    "compute_karmic_sfc",
    "compute_material_sfc",
    "compute_utai_aggregate",
    "render_financial_profile",
    "render_utai_profile",
]
