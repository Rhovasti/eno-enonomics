"""Tests for the alchemical sector in the financial layer (no Minsky dependency)."""

from ..citystates.parser import CitystateSpec
from ..financial.analysis import compute_financial_analysis
from ..financial.narrative import SECTORS, _godley_transactions, render_financial_profile
from ..financial.parameters import FINANCIAL_PARAMS
from ..financial.sfc import compute_material_sfc


def _spec() -> CitystateSpec:
    return CitystateSpec(
        name="Testia",
        founded_cycle=100,
        population=10000,
        growth_rate=0.01,
        temporal_state="Day",
        valley="Day",
        latitude=45.0,
        longitude=30.0,
    )


def _economy() -> tuple:
    supply = {"wood": 100.0, "cunu": 10.0, "sap": 5.0, "living-bronze": 2.0}
    demand: dict[str, float] = {"wood": 80.0}
    prices = {"wood": 1.0, "cunu": 5.0, "sap": 4.0, "living-bronze": 50.0}
    return supply, demand, prices


def test_alchemical_value_added_counts_only_alchemical_production() -> None:
    supply, demand, prices = _economy()
    m = compute_material_sfc(_spec(), supply, demand, prices)

    # cunu (element): 10*5=50, sap (component): 5*4=20, living-bronze (stuff): 2*50=100.
    assert m.alchemical_split["element"] == 50.0
    assert m.alchemical_split["component"] == 20.0
    assert m.alchemical_split["stuff"] == 100.0
    assert m.alchemical_value_added == 170.0
    # GDP also contains mundane wood production.
    assert m.gdp == 170.0 + 100.0


def test_guild_flows_consistent() -> None:
    supply, demand, prices = _economy()
    spec = _spec()
    m = compute_material_sfc(spec, supply, demand, prices)
    wage_share = FINANCIAL_PARAMS["Day"]["wage_share"]

    assert m.guild_wages == wage_share * m.alchemical_value_added
    assert m.guild_surplus == m.alchemical_value_added - m.guild_wages
    # Guild consumption is the alchemical share of household spending.
    assert m.guild_consumption == m.consumption * (m.alchemical_value_added / m.gdp)


def test_godley_rows_sum_to_zero_and_guild_column_balances() -> None:
    analysis = compute_financial_analysis(_spec(), *_economy())
    rows = _godley_transactions(analysis)

    for label, cells in rows:
        assert abs(sum(cells.values())) < 1e-9, f"row {label} does not balance"

    guild_balance = sum(cells.get("Guild", 0.0) for _, cells in rows)
    assert abs(guild_balance) < 1e-9  # va - w_a - d_a = 0 by construction


def test_narrative_renders_guild_column() -> None:
    analysis = compute_financial_analysis(_spec(), *_economy())
    text = render_financial_profile(analysis)

    for sector in SECTORS:
        assert sector in text
    assert "Alchemists' Guild value added" in text
    assert "Alchemical consumption" in text
    assert "Guild dividends" in text
