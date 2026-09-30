"""Render dynamic citystate histories into narrative markdown chronicles.

Each chronicle reads like a historical account: founding, population trajectory,
technological development, economic eras (extractive booms/busts vs renewable
mainstays), trade character, and the cycle-998 state. Only **extractive** resources
(mines/elements) are described as depleting; renewable resources (food/wood/crafted)
are described as mainstays whose stocks track population.
"""

from .parser import CitystateSpec


def _cycle(history: dict, index: int) -> int:
    return history["founded_cycle"] + int(history["time"][index])


def _tier_name(tech_level: float) -> str:
    if tech_level < 1.0:
        return "tribal"
    if tech_level < 2.0:
        return "medieval"
    return "industrial"


def _fmt_pop(value: float) -> str:
    return f"{round(value):,}"


def _first_crossing(values: list[float], threshold: float) -> int | None:
    for i, v in enumerate(values):
        if v >= threshold:
            return i
    return None


def extract_milestones(history: dict, spec: CitystateSpec, extractive: set[str]) -> dict:
    """Extract key narrative milestones from a citystate's dynamic history."""
    pop = history["population"]
    tech = history["tech"]
    founded = history["founded_cycle"]

    pop_peak_i = pop.index(max(pop))
    pop_ratio = pop[-1] / pop[0] if pop[0] else 1.0

    medieval_i = _first_crossing(tech, 1.0)
    industrial_i = _first_crossing(tech, 2.0)
    medieval_cycle = _cycle(history, medieval_i) if medieval_i else None
    industrial_cycle = _cycle(history, industrial_i) if industrial_i else None
    if tech[0] >= 1.0:
        medieval_cycle = founded
    if tech[0] >= 2.0:
        industrial_cycle = founded

    resource_events = []
    for resource in history["resources"]:
        stocks = history["stocks"].get(resource, [])
        if not stocks or max(stocks) < 1:
            continue
        peak_i = stocks.index(max(stocks))
        peak = max(stocks)
        final = stocks[-1]
        resource_events.append(
            {
                "resource": resource,
                "peak": peak,
                "peak_cycle": _cycle(history, peak_i),
                "final": final,
                "depletion": final / peak if peak > 0 else 1.0,
                "extractive": resource in extractive,
            }
        )
    resource_events.sort(key=lambda e: -e["final"])

    def _avg_trade(index: int) -> float:
        vals = [
            history["trade"][r][index] for r in history["trade"] if len(history["trade"][r]) > index
        ]
        return sum(vals) / len(vals) if vals else 0.0

    return {
        "founded": founded,
        "run_cycles": int(history["time"][-1]) if history["time"] else 0,
        "temporal_state": spec.temporal_state,
        "valley": spec.valley,
        "pop_initial": pop[0],
        "pop_final": pop[-1],
        "pop_peak": max(pop),
        "pop_peak_cycle": _cycle(history, pop_peak_i),
        "pop_ratio": pop_ratio,
        "tech_initial": tech[0],
        "tech_final": tech[-1],
        "medieval_cycle": medieval_cycle,
        "industrial_cycle": industrial_cycle,
        "resource_events": resource_events,
        "trade_end": _avg_trade(-1),
    }


def _population_narrative(m: dict) -> str:
    ratio = m["pop_ratio"]
    if ratio > 1.3:
        arc = f"grew robustly from {_fmt_pop(m['pop_initial'])} to {_fmt_pop(m['pop_final'])}"
    elif ratio > 1.05:
        arc = f"grew modestly from {_fmt_pop(m['pop_initial'])} to {_fmt_pop(m['pop_final'])}"
    elif ratio < 0.7:
        arc = f"declined from {_fmt_pop(m['pop_initial'])} to {_fmt_pop(m['pop_final'])}"
    elif ratio < 0.95:
        arc = f"slowly declined from {_fmt_pop(m['pop_initial'])} to {_fmt_pop(m['pop_final'])}"
    else:
        arc = f"remained roughly stable near {_fmt_pop(m['pop_initial'])}"
    peak_note = ""
    if m["pop_peak"] > m["pop_final"] * 1.15:
        peak_note = f", peaking at {_fmt_pop(m['pop_peak'])} around cycle {m['pop_peak_cycle']}"
    return f"Over the {m['run_cycles']} cycles of its recorded history, the population {arc}{peak_note}."


def _tech_narrative(m: dict) -> str:
    initial = _tier_name(m["tech_initial"])
    if m["industrial_cycle"] and m["industrial_cycle"] > m["founded"] and m["tech_initial"] < 2.0:
        main = f"advanced from {initial} to industrial around cycle {m['industrial_cycle']}"
    elif m["medieval_cycle"] and m["medieval_cycle"] > m["founded"] and m["tech_initial"] < 1.0:
        main = f"advanced from tribal to medieval around cycle {m['medieval_cycle']}"
    else:
        main = f"remained {initial}"
    if m["tech_final"] < 1.0:
        tail = f", its tech level rising only to {m['tech_final']:.2f}"
    elif m["tech_final"] >= 2.0:
        tail = f", reaching full industrial maturity (T={m['tech_final']:.1f})"
    else:
        tail = ""
    return f"The settlement {main}{tail} by cycle 998."


def _resource_eras(m: dict) -> list[str]:
    """Narrative lines: extractive depletion stories + renewable mainstays."""
    lines = []
    extractive_events = [e for e in m["resource_events"] if e["extractive"]]
    renewable_events = [e for e in m["resource_events"] if not e["extractive"]]

    if extractive_events:
        for ev in extractive_events[:3]:
            dep = ev["depletion"]
            if dep < 0.2:
                verdict = f"before being largely exhausted (down to {ev['final']:,.0f}) — a classic extractive bust"
            elif dep < 0.6:
                verdict = f"before declining to {ev['final']:,.0f} as deposits thinned"
            else:
                verdict = f"and remained productive at {ev['final']:,.0f}"
            lines.append(
                f"- **{ev['resource']}** (extractive): peaked at {ev['peak']:,.0f} around cycle {ev['peak_cycle']}, {verdict}."
            )
    else:
        lines.append("- No major extractive industries defined its history.")

    mainstays = [e["resource"] for e in renewable_events[:3] if e["final"] > 1]
    if mainstays:
        lines.append(f"- Renewable mainstays: {', '.join(mainstays)}.")
    return lines


def _trade_narrative(m: dict) -> str:
    if m["trade_end"] > 0:
        return "a net importer, dependent on trade for staples it could not fully produce"
    if m["trade_end"] < 0:
        return "a net exporter, sending its surplus to neighbors"
    return "broadly self-sufficient in trade"


def render_chronicle(history: dict, spec: CitystateSpec, extractive: set[str]) -> str:
    """Render a citystate's dynamic history as a narrative markdown chronicle."""
    m = extract_milestones(history, spec, extractive)
    name = spec.name

    depleted = any(e["extractive"] and e["depletion"] < 0.3 for e in m["resource_events"])
    lines = [
        f"# Economic Chronicle: {name}",
        "",
        (
            f"**{name}** was founded in cycle {m['founded']} in {m['valley']} Valley — a "
            f"{m['temporal_state']}-temporal settlement of {_fmt_pop(m['pop_initial'])} souls. "
            f"What follows is the economic history of its {m['run_cycles']}-cycle recorded lifespan, to cycle 998."
        ),
        "",
        "## Population",
        "",
        _population_narrative(m),
        "",
        "## Technology",
        "",
        _tech_narrative(m),
        "",
        "## Economic Eras",
        "",
        *_resource_eras(m),
        "",
        "## Trade",
        "",
        f"Throughout its history, {name} was {_trade_narrative(m)}.",
        "",
        "## At Cycle 998",
        "",
        (
            f"By cycle 998, {name} had a population of {_fmt_pop(m['pop_final'])} "
            f"(×{m['pop_ratio']:.2f} of its founding size), a {_tier_name(m['tech_final'])} economy, "
            f"and {'its mines were largely spent' if depleted else 'a stable resource base'}."
        ),
        "",
    ]

    top_final = m["resource_events"][:5]
    if top_final:
        lines.append("| Resource | Peak | At 998 | Status |")
        lines.append("|---|---|---|---|")
        for ev in top_final:
            if ev["extractive"]:
                status = (
                    "depleted"
                    if ev["depletion"] < 0.3
                    else "declining"
                    if ev["depletion"] < 0.7
                    else "active"
                )
            else:
                status = "renewable"
            lines.append(
                f"| {ev['resource']} | {ev['peak']:,.0f} | {ev['final']:,.0f} | {status} |"
            )
        lines.append("")

    return "\n".join(lines)


__all__ = ["extract_milestones", "render_chronicle"]
