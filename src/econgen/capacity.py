"""Production capacity calculation and management."""

import logging
from decimal import Decimal
from typing import Any

from .models import Capacity, Operator, ProductionRule, TechLevel
from .rules import RulesEngine
from .util import clamp

logger = logging.getLogger(__name__)


class CapacityCalculator:
    """Calculate and manage production capacities for operators."""

    def __init__(self, rules_engine: RulesEngine):
        """Initialize capacity calculator.

        Args:
            rules_engine: Production rules engine
        """
        self.rules_engine = rules_engine
        self._capacity_cache: dict[str, list[Capacity]] = {}
        logger.info("Initialized capacity calculator")

    def calculate_all_capacities(self, operators: list[Operator]) -> list[Capacity]:
        """Calculate production capacities for all operators.

        Args:
            operators: List of economic operators

        Returns:
            List of all calculated capacities
        """
        logger.info(f"Calculating capacities for {len(operators)} operators")
        all_capacities = []

        for operator in operators:
            capacities = self.calculate_operator_capacities(operator)
            all_capacities.extend(capacities)

        logger.info(f"Calculated {len(all_capacities)} total capacity assignments")
        return all_capacities

    def calculate_operator_capacities(self, operator: Operator) -> list[Capacity]:
        """Calculate all production capacities for a single operator.

        Args:
            operator: Economic operator

        Returns:
            List of capacities for this operator
        """
        # Check cache first
        cache_key = f"{operator.operator_id}_{hash(str(operator.model_dump()))}"
        if cache_key in self._capacity_cache:
            return self._capacity_cache[cache_key]

        capacities = []
        eligible_rules = self.rules_engine.get_eligible_rules(operator)

        logger.debug(f"Calculating {len(eligible_rules)} capacities for {operator.name}")

        for rule in eligible_rules:
            try:
                capacity = self._calculate_single_capacity(operator, rule)
                if capacity.max_rate > 0:  # Only include positive capacities
                    capacities.append(capacity)
            except Exception as e:  # noqa: BLE001 - skip the rule, keep the others
                logger.warning(
                    f"Failed to calculate capacity for {operator.operator_id} + {rule.rule_id}: {e}"
                )

        # Cache result
        self._capacity_cache[cache_key] = capacities
        return capacities

    def _calculate_single_capacity(self, operator: Operator, rule: ProductionRule) -> Capacity:
        """Calculate capacity for single operator-rule pair with detailed logic.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Calculated capacity
        """
        base_capacity = Decimal("1.0")
        efficiency = Decimal("1.0")

        # Population-based scaling (labor availability)
        labor_capacity = self._calculate_labor_capacity(operator, rule)
        base_capacity *= labor_capacity

        # Endowment-based scaling
        endowment_capacity = self._calculate_endowment_capacity(operator, rule)
        base_capacity *= endowment_capacity

        # Technology-based scaling
        tech_capacity = self._calculate_tech_capacity(operator, rule)
        base_capacity *= tech_capacity

        # Infrastructure bonuses
        infrastructure_bonus = self._calculate_infrastructure_bonus(operator, rule)
        base_capacity *= infrastructure_bonus

        # Specialization bonus (based on tags)
        specialization_bonus = self._calculate_specialization_bonus(operator, rule)
        base_capacity *= specialization_bonus

        # Calculate efficiency factors
        efficiency = self._calculate_efficiency(operator, rule)

        # Apply constraints and bounds
        base_capacity = self._apply_capacity_constraints(base_capacity, operator, rule)

        return Capacity(
            operator_id=operator.operator_id,
            rule_id=rule.rule_id,
            max_rate=base_capacity,
            efficiency=efficiency,
        )

    def _calculate_labor_capacity(self, operator: Operator, rule: ProductionRule) -> Decimal:
        """Calculate labor-based capacity scaling.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Labor capacity multiplier
        """
        if operator.population <= 0:
            return Decimal("0.1")  # Minimal capacity without population

        # Reason: output must scale linearly with workforce so that supply is comparable
        # to per-capita demand; the absolute scale is set later by calibration.
        workforce = Decimal(operator.population) / Decimal(1000)
        if rule.labor_required > 0:
            return workforce / rule.labor_required
        return workforce

    def _calculate_endowment_capacity(self, operator: Operator, rule: ProductionRule) -> Decimal:
        """Calculate endowment-based capacity scaling.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Endowment capacity multiplier
        """
        if not rule.capacity_driver:
            return Decimal("1.0")

        endowment_value = operator.endowments.get(rule.capacity_driver, Decimal(0))

        if endowment_value <= 0:
            return Decimal("0.1")  # Very low capacity without required endowment

        # Endowment provides 1x to 4x multiplier with diminishing returns
        # Formula: 1 + endowment * 3 * (1 - exp(-endowment))
        scaling_factor = endowment_value * Decimal("3.0")
        # Approximate diminishing returns without using exp
        if endowment_value > Decimal("0.5"):
            scaling_factor *= Decimal("1.0") - (endowment_value - Decimal("0.5")) / Decimal("2.0")

        return Decimal("1.0") + clamp(scaling_factor, Decimal(0), Decimal("3.0"))

    def _calculate_tech_capacity(self, operator: Operator, rule: ProductionRule) -> Decimal:
        """Calculate technology-based capacity scaling.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Technology capacity multiplier
        """
        # Base multipliers by tech level
        base_multipliers = {
            TechLevel.TRIBAL: Decimal("0.5"),
            TechLevel.MEDIEVAL: Decimal("1.0"),
            TechLevel.INDUSTRIAL: Decimal("2.0"),
        }

        base_mult = base_multipliers[operator.tech]

        # Bonus for tech level above minimum requirement
        if TechLevel(operator.tech) > TechLevel(rule.tech_min):
            tech_levels = [TechLevel.TRIBAL, TechLevel.MEDIEVAL, TechLevel.INDUSTRIAL]
            op_idx = tech_levels.index(operator.tech)
            rule_idx = tech_levels.index(rule.tech_min)
            tech_advantage = op_idx - rule_idx

            # 20% bonus per tech level advantage
            tech_bonus = Decimal("1.0") + (Decimal("0.2") * tech_advantage)
            base_mult *= tech_bonus

        return base_mult

    def _calculate_infrastructure_bonus(self, operator: Operator, rule: ProductionRule) -> Decimal:
        """Calculate infrastructure-based capacity bonus.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Infrastructure bonus multiplier
        """
        bonus = Decimal("1.0")

        # Port bonus for relevant activities
        if operator.port:
            port_rules = ["fishing", "trade", "import", "export", "shipbuilding"]
            if any(port_rule in rule.rule_id for port_rule in port_rules):
                bonus *= Decimal("1.5")

        # Plaza/market bonus for trade and crafts
        if operator.plaza:
            market_rules = ["craft", "trade", "jewelry", "textile", "tool"]
            if any(market_rule in rule.rule_id for market_rule in market_rules):
                bonus *= Decimal("1.3")

        # Temple bonus for luxury goods and cultural items
        if operator.temple:
            cultural_rules = ["jewelry", "art", "luxury", "ceremonial"]
            if any(cult_rule in rule.rule_id for cult_rule in cultural_rules):
                bonus *= Decimal("1.2")

        # Walls provide general defensive production bonus
        if operator.walls:
            defensive_rules = ["quarrying", "fortification"]
            if any(def_rule in rule.rule_id for def_rule in defensive_rules):
                bonus *= Decimal("1.1")

        return bonus

    def _calculate_specialization_bonus(self, operator: Operator, rule: ProductionRule) -> Decimal:
        """Calculate specialization bonus based on operator tags and culture.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Specialization bonus multiplier
        """
        bonus = Decimal("1.0")

        # Check tag-based specializations
        for tag in operator.tags:
            tag_lower = tag.lower()
            rule_lower = rule.rule_id.lower()

            # Cultural specializations
            if "culture_noon" in tag_lower and "agriculture" in rule_lower:
                bonus *= Decimal("1.3")  # Noon culture good at farming
            elif "culture_night" in tag_lower and "craft" in rule_lower:
                bonus *= Decimal("1.3")  # Night culture good at crafts
            elif "culture_dawn" in tag_lower and "trade" in rule_lower:
                bonus *= Decimal("1.3")  # Dawn culture good at trade
            elif "culture_drifters" in tag_lower and "gather" in rule_lower:
                bonus *= Decimal("1.2")  # Drifters good at gathering

            # Religious specializations
            if "religion_asta" in tag_lower and "jewelry" in rule_lower:
                bonus *= Decimal("1.2")  # Asta religion values craftsmanship

        # Capital city bonus
        if operator.capital:
            bonus *= Decimal("1.1")

        return bonus

    def _calculate_efficiency(self, operator: Operator, rule: ProductionRule) -> Decimal:
        """Calculate operational efficiency.

        Args:
            operator: Economic operator
            rule: Production rule

        Returns:
            Efficiency factor (0.1 to 2.0)
        """
        efficiency = Decimal("1.0")

        # Population density effects (too crowded or too sparse reduces efficiency)
        if operator.population > 0:
            pop_density = Decimal(str(operator.population))

            # Optimal range is 5,000 to 50,000 population
            if pop_density < 5000:
                efficiency *= (pop_density / Decimal(5000)) * Decimal("0.3") + Decimal("0.7")
            elif pop_density > 50000:
                # Diminishing returns from overcrowding
                excess = (pop_density - Decimal(50000)) / Decimal(50000)
                efficiency *= max(Decimal("0.8"), Decimal("1.0") - excess * Decimal("0.1"))

        # Infrastructure efficiency
        infrastructure_count = sum(
            [operator.plaza, operator.citadel, operator.walls, operator.temple, operator.port]
        )
        infrastructure_bonus = Decimal("1.0") + (
            Decimal(str(infrastructure_count)) * Decimal("0.05")
        )
        efficiency *= infrastructure_bonus

        return clamp(efficiency, Decimal("0.1"), Decimal("2.0"))

    def _apply_capacity_constraints(
        self, capacity: Decimal, operator: Operator, rule: ProductionRule
    ) -> Decimal:
        """Apply final constraints and bounds to capacity.

        Args:
            capacity: Calculated capacity
            operator: Economic operator
            rule: Production rule

        Returns:
            Constrained capacity
        """
        # Shanty towns have reduced capacity due to poor conditions
        if operator.shanty_town:
            capacity *= Decimal("0.7")

        # Always allow minimal production; no upper cap since calibration sets the scale
        return max(capacity, Decimal("0.01"))

    def get_capacity_summary(self, capacities: list[Capacity]) -> dict[str, Any]:
        """Get summary statistics about capacities.

        Args:
            capacities: List of capacity assignments

        Returns:
            Dictionary with capacity statistics
        """
        if not capacities:
            return {"total_capacities": 0}

        total_capacities = len(capacities)
        total_max_rate = sum(c.max_rate for c in capacities)
        avg_efficiency = sum(c.efficiency for c in capacities) / total_capacities

        # Group by operator
        by_operator: dict[str, list[Capacity]] = {}
        for capacity in capacities:
            if capacity.operator_id not in by_operator:
                by_operator[capacity.operator_id] = []
            by_operator[capacity.operator_id].append(capacity)

        return {
            "total_capacities": total_capacities,
            "total_max_rate": float(total_max_rate),
            "average_efficiency": float(avg_efficiency),
            "operators_with_capacity": len(by_operator),
            "avg_capacities_per_operator": total_capacities / len(by_operator),
            "max_single_capacity": float(max(c.max_rate for c in capacities)),
            "min_single_capacity": float(min(c.max_rate for c in capacities)),
        }

    def clear_cache(self) -> None:
        """Clear capacity calculation cache."""
        self._capacity_cache.clear()
        logger.info("Cleared capacity calculation cache")


# Export main class
__all__ = ["CapacityCalculator"]
