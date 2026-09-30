"""Data tables for the citystate governance catalog.

Pure data (no matching logic): the ~45-type catalog, hard-coded lore
assignments, state-field patterns and founding-era type sets.
"""

from dataclasses import dataclass, field


@dataclass
class GovType:
    name: str
    category: str
    eno_note: str
    temporal_states: set[str] = field(default_factory=set)
    valleys: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    infrastructure: set[str] = field(default_factory=set)
    avoid_infra: set[str] = field(default_factory=set)
    pop_max: int = 999999
    pop_min: int = 0
    economic: str = ""  # "crisis" / "prosperous" / "trade_surplus" / "large_gdp" / ""
    state_field: set[str] = field(default_factory=set)  # preferred state field values


# === Curated governance catalog (~30 types) ===
CATALOG: list[GovType] = [
    GovType(
        "Acephalous Society",
        "Kinship & Non-State",
        "Day Valley nomads; free people without permanent leaders.",
        temporal_states={"Drifters", "Wildlands", "Day"},
        valleys={"Day"},
        pop_max=3000,
        avoid_infra={"citadel", "walls"},
    ),
    GovType(
        "Segmentary Lineage",
        "Kinship & Non-State",
        "Highland nomads; close-knit family units that fuse against threats.",
        temporal_states={"Drifters", "Wildlands"},
        tags={"highland", "nomadic"},
        pop_max=5000,
    ),
    GovType(
        "Segmentary State (Mandala)",
        "Kinship & Non-State",
        "Large citystate with soft, fading sphere of influence.",
        state_field={"Regional Capital"},
        pop_min=10000,
    ),
    GovType(
        "Age-Grade System",
        "Kinship & Non-State",
        "Aumian subterranean tribes; responsibilities shift with age.",
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"underground", "subterranean"},
        pop_max=8000,
    ),
    GovType(
        "Heterarchy",
        "Kinship & Non-State",
        "Dawn Valley; different leaders hold power in different contexts.",
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"multicultural"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Absolute Monarchy",
        "Autocracy & Monarchy",
        "Unlimited sovereign authority in a single ruler.",
        tags={"capital", "monarchy"},
        infrastructure={"citadel", "walls"},
        state_field={"Capital"},
        temporal_states={"Dusk", "Noon"},
    ),
    GovType(
        "Constitutional Monarchy",
        "Autocracy & Monarchy",
        "Crown restricted by legal framework; progressive transition.",
        tags={"capital"},
        infrastructure={"plaza"},
        temporal_states={"Day"},
        state_field={"Capital"},
        economic="prosperous",
    ),
    GovType(
        "Diarchy",
        "Autocracy & Monarchy",
        "Two rulers from different cultural groups share governance.",
        tags={"multicultural", "bicultural"},
        infrastructure={"citadel", "plaza"},
        temporal_states={"Day", "Dusk"},
    ),
    GovType(
        "Elective Monarchy",
        "Autocracy & Monarchy",
        "Council elects the monarch from eligible noble houses.",
        valleys={"Day"},
        tags={"capital", "peak-power"},
        infrastructure={"plaza"},
        temporal_states={"Day"},
    ),
    GovType(
        "Aristocracy",
        "Oligarchy & Minority Rule",
        "Rule by hereditary landed elite.",
        infrastructure={"citadel", "walls"},
        tags={"aristocratic", "noble"},
        temporal_states={"Dusk", "Noon"},
        avoid_infra={"shanty_town"},
    ),
    GovType(
        "Plutocracy",
        "Oligarchy & Minority Rule",
        "Rule by the wealthy; the state extracts for the elite.",
        tags={"peak-power"},
        economic="large_gdp",
        state_field={"Valar Dominion of Worth"},
    ),
    GovType(
        "Stratocracy",
        "Oligarchy & Minority Rule",
        "Direct military rule; civil and military command fused.",
        tags={"military", "fortress", "citadel"},
        infrastructure={"citadel", "walls"},
        temporal_states={"Night"},
        state_field={"Capital"},
    ),
    GovType(
        "Technocracy",
        "Oligarchy & Minority Rule",
        "Rule by technical experts based on data and science.",
        tags={"industrial", "scholarly"},
        temporal_states={"Day", "Dawn"},
        economic="prosperous",
    ),
    GovType(
        "Gerontocracy",
        "Oligarchy & Minority Rule",
        "Governance by the eldest members; wisdom over innovation.",
        temporal_states={"Noon", "Dusk"},
        infrastructure={"temple"},
        tags={"stagnant", "traditional"},
    ),
    GovType(
        "Theocracy",
        "Theocracy & Ideological",
        "Clerical class governs through divine law.",
        infrastructure={"temple"},
        tags={"religious", "sacred", "temple"},
        temporal_states={"Dusk", "Night"},
    ),
    GovType(
        "Direct Democracy",
        "Democratic & Republican",
        "Citizens vote directly on laws and policies.",
        infrastructure={"plaza"},
        temporal_states={"Day"},
        pop_max=8000,
        economic="prosperous",
    ),
    GovType(
        "Sortition (Demarchy)",
        "Democratic & Republican",
        "Leaders chosen by lottery; Erno's ideal of chance governance.",
        infrastructure={"plaza"},
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"innovative"},
    ),
    GovType(
        "Consociationalism",
        "Democratic & Republican",
        "Power-sharing for deeply divided multicultural societies.",
        tags={"multicultural"},
        pop_min=5000,
        temporal_states={"Day", "Dusk"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Guild Socialism",
        "Socialist Experiment",
        "Workers run industries via autonomous guilds.",
        tags={"industrial"},
        temporal_states={"Day", "Dawn"},
        infrastructure={"plaza"},
        economic="prosperous",
    ),
    GovType(
        "Merchant City Republic",
        "Democratic & Republican",
        "Port city governed by merchant elites and trade councils.",
        infrastructure={"port"},
        tags={"commercial", "trade"},
        state_field={"Independent"},
        economic="trade_surplus",
    ),
    GovType(
        "Chiefdom",
        "Tribal & Early Agricultural",
        "Tribal sedentary society led by a chief.",
        tags={"tribal"},
        state_field={"Settlement"},
        pop_max=5000,
        temporal_states={"Drifters", "Wildlands", "Dawn"},
    ),
    GovType(
        "Council of Elders",
        "Tribal & Early Agricultural",
        "Village governed by a council of the eldest and wisest.",
        infrastructure={"temple", "plaza"},
        state_field={"Council of Zmur", "Settlement"},
        pop_max=6000,
        temporal_states={"Dusk", "Noon"},
    ),
    GovType(
        "Warrior Aristocracy",
        "Tribal & Early Agricultural",
        "Military elite rules from fortified positions.",
        tags={"military", "fortress", "warrior"},
        infrastructure={"walls", "citadel"},
        temporal_states={"Night", "Dusk"},
    ),
    GovType(
        "Kakistocracy",
        "Fringe",
        "Government by the least qualified; a failed or corrupt state.",
        temporal_states={"Night", "Symbiotic Decline"},
        tags={"crisis", "failed"},
        infrastructure={"shanty_town"},
        economic="crisis",
    ),
    GovType(
        "Ochlocracy",
        "Fringe",
        "Mob rule; the passions of the masses override law.",
        temporal_states={"Night"},
        tags={"fear-driven", "crisis"},
        pop_min=10000,
        economic="crisis",
    ),
    GovType(
        "Irrigation Bureaucracy",
        "Fringe",
        "Hydraulic despotism around a great dam.",
        valleys={"Dawn"},
        infrastructure={"river access", "farms"},
        tags={"dam", "irrigation"},
    ),
    GovType(
        "Minarchism",
        "Libertarian & Anarchist",
        "Night-watchman state; minimal governance in Dusk Valley.",
        valleys={"Dusk"},
        state_field={"Independent"},
        temporal_states={"Dusk"},
        avoid_infra={"citadel"},
    ),
    GovType(
        "Secret Society Governance",
        "Fringe",
        "Shadowy elite governs through secrets and information control.",
        infrastructure={"temple"},
        tags={"mysterious", "secret"},
        state_field={"Citadel of Almo"},
    ),
    GovType(
        "Corporate Sovereignty",
        "Libertarian & Anarchist",
        "Trade company governs territory as a corporate entity.",
        infrastructure={"port"},
        tags={"commercial", "industrial"},
        state_field={"Trade Company of Ataria", "Independent"},
    ),
    GovType(
        "Sacred Kingship",
        "Theocracy & Ideological",
        "Divine ruler combining temporal and spiritual authority.",
        infrastructure={"temple", "citadel"},
        tags={"religious", "sacred", "capital"},
        temporal_states={"Dusk"},
    ),
    GovType(
        "Charter City",
        "Libertarian & Anarchist",
        "Semi-autonomous innovation zone attracting investment.",
        infrastructure={"port"},
        valleys={"Dawn"},
        temporal_states={"Dawn"},
        tags={"innovative", "commercial"},
        pop_max=15000,
    ),
    GovType(
        "Pirate/Outlaw Governance",
        "Fringe",
        "Floating direct-democracy of seafarers outside the law.",
        infrastructure={"port"},
        tags={"sea", "raider", "nomadic"},
        temporal_states={"Drifters", "Wildlands", "Winds"},
        pop_max=8000,
    ),
    # --- Expanded types (+15) ---
    GovType(
        "Cybernetic Socialism",
        "Socialist Experiment",
        "Economy managed in real-time by soulsphere feedback loops (Project Cybersyn style).",
        tags={"constructed", "soulsphere", "algorithmic"},
        temporal_states={"Day", "Dawn"},
        economic="prosperous",
    ),
    GovType(
        "Oriental Despotism",
        "Autocracy & Monarchy",
        "Hydraulic empire; centralized bureaucratic despotism around water infrastructure.",
        infrastructure={"river access"},
        tags={"dam", "hydraulic", "lake"},
        valleys={"Dawn"},
    ),
    GovType(
        "Personalist Dictatorship",
        "Autocracy & Monarchy",
        "Power rests on charisma or military backing, untethered to royal lineage.",
        tags={"autocrat", "dictator"},
        temporal_states={"Night"},
        infrastructure={"citadel"},
    ),
    GovType(
        "Kritarchy",
        "Oligarchy & Minority Rule",
        "Rule by judges; governance through a legal system and courts.",
        tags={"legal", "judge", "court"},
        infrastructure={"plaza"},
        temporal_states={"Dusk"},
    ),
    GovType(
        "Noocracy",
        "Oligarchy & Minority Rule",
        "Rule by philosophers and intellectuals; wisdom-based governance.",
        tags={"scholarly", "philosopher", "wise"},
        temporal_states={"Day", "Noon"},
        infrastructure={"temple"},
    ),
    GovType(
        "Anarcho-Syndicalism",
        "Socialist Experiment",
        "Stateless society organized into worker-run trade unions.",
        tags={"worker", "union", "industrial"},
        temporal_states={"Day"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Council Communism",
        "Socialist Experiment",
        "Governance through local democratic workers' councils.",
        tags={"council", "soviet", "worker"},
        temporal_states={"Day", "Dawn"},
        infrastructure={"plaza"},
    ),
    GovType(
        "Libertarian Municipalism",
        "Socialist Experiment",
        "State dissolved into neighborhood assemblies using direct democracy.",
        infrastructure={"plaza"},
        temporal_states={"Dawn", "Day"},
        tags={"community", "assembly"},
        pop_max=10000,
    ),
    GovType(
        "Timocracy",
        "Oligarchy & Minority Rule",
        "Rule by property owners valuing honor and civic virtue.",
        tags={"property", "honor", "landowner"},
        temporal_states={"Dusk"},
        economic="prosperous",
    ),
    GovType(
        "Big-man Society",
        "Kinship & Non-State",
        "Pre-state prestige-based governance; influence through generosity.",
        tags={"tribal", "nomadic"},
        temporal_states={"Drifters", "Wildlands", "Dawn"},
        pop_max=3000,
    ),
    GovType(
        "Temple Economy",
        "Theocracy & Ideological",
        "Temple-centered redistribution; priests control production and storage.",
        infrastructure={"temple"},
        tags={"religious", "sacred", "redistribution"},
        temporal_states={"Dusk", "Noon"},
    ),
    GovType(
        "Palace Economy",
        "Autocracy & Monarchy",
        "Palace-centered redistribution; elite controls all production.",
        infrastructure={"citadel"},
        tags={"palace", "royal"},
        temporal_states={"Dusk", "Noon"},
        state_field={"Capital"},
    ),
    GovType(
        "Village Republic",
        "Democratic & Republican",
        "Small self-governing village with direct citizen participation.",
        infrastructure={"plaza"},
        temporal_states={"Day", "Dawn"},
        pop_max=4000,
        economic="prosperous",
    ),
    GovType(
        "Tribal Confederation",
        "Kinship & Non-State",
        "League of independent tribes united for mutual defense.",
        tags={"tribal", "confederation", "nomadic"},
        temporal_states={"Drifters", "Wildlands"},
        pop_min=3000,
    ),
    GovType(
        "Panarchy",
        "Libertarian & Anarchist",
        "Multiple governance types coexist; citizens choose their political provider.",
        tags={"multicultural", "diverse", "pluralist"},
        temporal_states={"Day"},
        infrastructure={"plaza"},
    ),
]


# Hard-coded lore assignments (name → type name).
LORE_ASSIGNMENTS: dict[str, str] = {
    "Citadel of Utaia": "Plutocracy",
    "Citadel of the Pass": "Stratocracy",
    "Citadel of Almo": "Secret Society Governance",
    "Guild": "Merchant City Republic",
    # Synthetic dam settlement; its "Hydraulic Dominion" state would otherwise
    # match the "dominion" -> Plutocracy state pattern.
    "Valvestrum": "Oriental Despotism",
}

# State-field pattern → governance type.
STATE_PATTERNS = {
    "council": "Council of Elders",
    "republic": "Direct Democracy",
    "trade company": "Corporate Sovereignty",
    "principality": "Constitutional Monarchy",
    "community": "Direct Democracy",
    "dominion": "Plutocracy",
}


# Root → preferred initial governance types (for founding-era assignment).
ROOT_TO_INITIAL: dict[str, list[str]] = {
    "Fortified Settlement": ["Chiefdom", "Warrior Aristocracy", "Absolute Monarchy"],
    "Trade Outpost": ["Big-man Society", "Merchant City Republic", "Acephalous Society"],
    "Fishing Village": ["Acephalous Society", "Village Republic", "Council of Elders"],
    "Agricultural Settlement": ["Council of Elders", "Chiefdom", "Heterarchy"],
    "Mining Camp": ["Big-man Society", "Stratocracy", "Chiefdom"],
    "Religious Sanctuary": ["Sacred Kingship", "Theocracy", "Council of Elders"],
    "Refuge Colony": ["Acephalous Society", "Consociationalism", "Segmentary Lineage"],
    "Nomadic Camp": ["Segmentary Lineage", "Tribal Confederation", "Acephalous Society"],
    "Political Experiment": ["Sortition (Demarchy)", "Heterarchy", "Direct Democracy"],
    "Administrative Center": ["Chiefdom", "Palace Economy", "Absolute Monarchy"],
    "Craft Settlement": ["Guild Socialism", "Heterarchy", "Council of Elders"],
    "Outlaw Haven": ["Pirate/Outlaw Governance", "Kakistocracy", "Acephalous Society"],
    "Hydraulic Settlement": ["Oriental Despotism", "Palace Economy", "Chiefdom"],
}

# Types considered "simple" (suitable for founding-era initial governance).
SIMPLE_CATEGORIES = {"Kinship & Non-State", "Tribal & Early Agricultural"}
SIMPLE_TYPES = {g.name for g in CATALOG if g.category in SIMPLE_CATEGORIES}
# Advanced types that are almost never initial (emerge through progression).
ADVANCED_TYPES = {
    "Cybernetic Socialism",
    "Technocracy",
    "Noocracy",
    "Kritarchy",
    "Anarcho-Syndicalism",
    "Council Communism",
    "Libertarian Municipalism",
    "Panarchy",
    "Timocracy",
    "Corporate Sovereignty",
}
