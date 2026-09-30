"""Financial behavioral parameters by temporal_state + labor tiers (from Eno lore).

Labor tiers from ``Economic System of Eno.md``:
Manual 1.0x, Apprentice 1.5x, Skilled 2.0x, Master 3.0x, Specialist 5.0x.

Financial behavioral params (wage_share, propensity_to_consume, savings_rate) are
derived from each citystate's temporal_state — crisis cities hoard and exploit;
innovative cities spend and invest.
"""

from typing import Dict

# (wage_share, propensity_to_consume, savings_rate) by temporal_state.
# wage_share: fraction of GDP paid as wages (rest = producer surplus).
# propensity: fraction of household income spent on consumption.
# savings_rate: fraction saved (= 1 - propensity, explicit for clarity).
FINANCIAL_PARAMS: Dict[str, Dict[str, float]] = {
    "Dawn": {"wage_share": 0.50, "propensity": 0.90, "savings_rate": 0.10},  # spend-heavy, invest
    "Day": {"wage_share": 0.60, "propensity": 0.80, "savings_rate": 0.20},  # balanced prosperity
    "Noon": {"wage_share": 0.55, "propensity": 0.75, "savings_rate": 0.25},  # stagnant, hoarding
    "Dusk": {"wage_share": 0.50, "propensity": 0.70, "savings_rate": 0.30},  # conservative
    "Night": {"wage_share": 0.40, "propensity": 0.60, "savings_rate": 0.40},  # crisis, hoarding
    "Drifters": {"wage_share": 0.55, "propensity": 0.85, "savings_rate": 0.15},
    "Wildlands": {"wage_share": 0.55, "propensity": 0.85, "savings_rate": 0.15},
    "Winds": {"wage_share": 0.50, "propensity": 0.80, "savings_rate": 0.20},
    "Symbiotic Decline": {"wage_share": 0.45, "propensity": 0.65, "savings_rate": 0.35},
    "Dwellers": {"wage_share": 0.50, "propensity": 0.75, "savings_rate": 0.25},
    "Autotrophic Founder": {"wage_share": 0.55, "propensity": 0.85, "savings_rate": 0.15},
}
DEFAULT_PARAMS: Dict[str, float] = {"wage_share": 0.50, "propensity": 0.80, "savings_rate": 0.20}

# Labor tiers: (name, wage_multiplier). From the Eno lore.
LABOR_TIERS = [
    ("Manual", 1.0),
    ("Apprentice", 1.5),
    ("Skilled", 2.0),
    ("Master", 3.0),
    ("Specialist", 5.0),
]

# Workforce fraction per tier, by tech level. More advanced = more skilled.
TIER_DISTRIBUTION: Dict[str, list] = {
    "tribal": [0.70, 0.20, 0.10, 0.00, 0.00],
    "medieval": [0.40, 0.30, 0.20, 0.10, 0.00],
    "industrial": [0.20, 0.25, 0.30, 0.20, 0.05],
}

# === Karmic Debt Hierarchy (from the Eno lore) ===
# 7 tiers of offenses, each 10x the previous. Base unit = Tier 3 (property offense).
# 1 life offense = 100,000 dignity offenses.
OFFENSE_TIERS = [
    ("dignity", 0.01),  # 1. insults, harassment
    ("privacy", 0.1),  # 2. trespass, surveillance, identity misuse
    ("property", 1.0),  # 3. theft, fraud, vandalism (BASE UNIT)
    ("liberty", 10.0),  # 4. coercion, kidnapping, unlawful detention
    ("bodily", 100.0),  # 5. assault, torture
    ("life", 1000.0),  # 6. homicide, murder
    ("society", 10000.0),  # 7. corruption, terrorism, genocide
]

# Intent multipliers (same harm judged differently by mental state).
INTENT_MULTIPLIERS = {"intentional": 1.0, "reckless": 0.9, "negligent": 0.8, "accidental": 0.7}

# Average intent weight by temporal_state (crisis cities = more intentional harm).
AVG_INTENT_BY_STATE: Dict[str, float] = {
    "Night": 0.90,
    "Symbiotic Decline": 0.88,
    "Noon": 0.80,
    "Dusk": 0.78,
    "Day": 0.75,
    "Dawn": 0.72,
    "Drifters": 0.75,
    "Wildlands": 0.78,
    "Winds": 0.82,
    "Dwellers": 0.76,
    "Autotrophic Founder": 0.74,
}
DEFAULT_AVG_INTENT = 0.78

# Offense rates: offenses per 1000 population per cycle, per tier [dignity..society].
# Crisis cities generate serious offenses (liberty/bodily/life); prosperous generate minor.
OFFENSE_RATES_BY_STATE: Dict[str, list] = {
    "Night": [50, 20, 10, 5, 2, 0.5, 0.01],  # crisis: heavy all tiers
    "Symbiotic Decline": [45, 18, 8, 4, 1.5, 0.3, 0.005],
    "Noon": [20, 8, 3, 0.5, 0.1, 0.01, 0],  # stagnant
    "Dusk": [25, 10, 4, 1, 0.2, 0.02, 0],  # declining
    "Day": [10, 3, 1, 0.1, 0.01, 0.001, 0],  # prosperous: minor only
    "Dawn": [15, 5, 2, 0.3, 0.05, 0.005, 0],  # growing
    "Drifters": [12, 4, 1.5, 0.2, 0.03, 0.003, 0],
    "Wildlands": [12, 4, 1.5, 0.2, 0.03, 0.003, 0],
    "Winds": [18, 7, 2.5, 0.4, 0.08, 0.008, 0],
    "Dwellers": [14, 5, 2, 0.3, 0.05, 0.005, 0],
    "Autotrophic Founder": [16, 6, 2, 0.3, 0.05, 0.005, 0],
}
DEFAULT_OFFENSE_RATES = [15, 5, 2, 0.3, 0.05, 0.005, 0]

# Forgiveness: fraction of accumulated debt that souls forgive (generating tokens).
# Most debts are forgiven before a soul passes (tokens become currency).
FORGIVENESS_RATE = 0.80

# Utaia's extraction rate on outstanding (unforgiven) debt.
UTAIA_EXTRACTION_RATE = 0.03  # 3%/cycle (within lore's 2-5% commission range).
