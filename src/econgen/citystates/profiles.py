"""Algebraic cycle-998 economic profile per citystate (Phase 2).

At steady state a city's net imports = consumption − production (flow balance), so
the profile is computed directly from the static supply/demand + world market
prices — no integration needed. The Minsky per-city harness (``simulator.py``)
returns in Phase 3 to produce dynamic *histories* with long-run drivers.
"""

from pydantic import BaseModel, Field

from ..taxonomy import ResourceTaxonomy
from .economy import tech_for
from .parser import CitystateSpec


class ResourceProfile(BaseModel):
    resource: str
    production: float
    consumption: float
    net_trade: float  # + = net import, - = net export
    stock: float
    price: float
    market_price: float
    role: str  # producer / consumer / balanced


class CitystateProfile(BaseModel):
    name: str
    founded_cycle: int
    final_cycle: int = 998
    temporal_state: str
    valley: str
    population: int
    tech: str
    resources: list[ResourceProfile]
    trade_balance: float  # value of net imports (+) / exports (-)
    top_exports: list[str]
    top_imports: list[str]
    specialization: list[str]
    character: str


class ProfileConfig(BaseModel):
    initial_stock_multiplier: float = Field(default=10.0, gt=0)
    consumer_baseline_stock: float = Field(default=50.0, ge=0)


def _role(production: float, consumption: float) -> str:
    if production > consumption * 1.1:
        return "producer"
    if consumption > production * 1.1:
        return "consumer"
    return "balanced"


def compute_citystate_profile(
    spec: CitystateSpec,
    supply: dict,
    demand: dict,
    market_prices: dict[str, float],
    taxonomy: ResourceTaxonomy,
    config: ProfileConfig,
) -> CitystateProfile:
    """Compute a steady-state (cycle-998) economic profile for one citystate."""
    from decimal import Decimal

    resources: list[ResourceProfile] = []
    for resource in sorted(set(supply) | set(demand)):
        production = float(supply.get(resource, Decimal(0)))
        consumption = float(demand.get(resource, Decimal(0)))
        if production <= 0 and consumption <= 0:
            continue
        net_trade = consumption - production  # + import, - export
        stock = (
            production * config.initial_stock_multiplier
            if production > 0
            else config.consumer_baseline_stock
        )
        # Price-taker: the city faces the world market price (mean of the role-based
        # scarcity prices across all citystates); fall back to the resource base price.
        market = market_prices.get(resource)
        if market is None:
            market = float(taxonomy.get_base_price(resource)) or 1.0
        resources.append(
            ResourceProfile(
                resource=resource,
                production=production,
                consumption=consumption,
                net_trade=net_trade,
                stock=stock,
                price=market,
                market_price=market,
                role=_role(production, consumption),
            )
        )

    trade_balance = sum(r.net_trade * r.market_price for r in resources)
    top_exports = [
        r.resource for r in sorted(resources, key=lambda x: x.net_trade) if r.net_trade < 0
    ][:3]
    top_imports = [
        r.resource for r in sorted(resources, key=lambda x: -x.net_trade) if r.net_trade > 0
    ][:3]
    specialization = [
        r.resource
        for r in sorted(resources, key=lambda x: -x.production * x.market_price)
        if r.production > 0
    ][:3]

    flow = "net importer" if trade_balance > 0 else "net exporter"
    char = (
        f"{spec.temporal_state} {spec.valley}-valley {spec.population:,}-pop city; "
        f"specializes in {', '.join(specialization) or 'little'}; {flow}."
    )

    return CitystateProfile(
        name=spec.name,
        founded_cycle=spec.founded_cycle,
        temporal_state=spec.temporal_state,
        valley=spec.valley,
        population=spec.population,
        tech=tech_for(spec),
        resources=resources,
        trade_balance=trade_balance,
        top_exports=top_exports,
        top_imports=top_imports,
        specialization=specialization,
        character=char,
    )


def render_profile(profile: CitystateProfile) -> str:
    """Render a profile as markdown."""
    lines = [
        f"# Economic Profile: {profile.name}",
        "",
        (
            f"- **State**: {profile.temporal_state} · **Valley**: {profile.valley} · "
            f"**Population**: {profile.population:,} · **Tech**: {profile.tech}"
        ),
        f"- **Founded**: cycle {profile.founded_cycle} · **Profiled at**: cycle {profile.final_cycle}",
        (
            f"- **Trade balance**: {profile.trade_balance:+.1f} (net "
            f"{'importer' if profile.trade_balance > 0 else 'exporter'})"
        ),
        f"- **Specialization**: {', '.join(profile.specialization) or 'none'}",
        f"- **Top exports**: {', '.join(profile.top_exports) or 'none'}",
        f"- **Top imports**: {', '.join(profile.top_imports) or 'none'}",
        "",
        "## Resources",
        "",
        "| Resource | Role | Production | Consumption | Net trade | Stock | Price | Market |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(profile.resources, key=lambda x: -abs(x.net_trade * x.market_price)):
        flow = "import" if r.net_trade > 0 else "export" if r.net_trade < 0 else "—"
        lines.append(
            f"| {r.resource} | {r.role} | {r.production:.1f} | {r.consumption:.1f} | "
            f"{flow} {abs(r.net_trade):.1f} | {r.stock:.0f} | {r.price:.2f} | {r.market_price:.2f} |"
        )
    lines.append("")
    lines.append(f"_{profile.character}_")
    return "\n".join(lines)


__all__ = [
    "CitystateProfile",
    "ProfileConfig",
    "ResourceProfile",
    "compute_citystate_profile",
    "render_profile",
]
