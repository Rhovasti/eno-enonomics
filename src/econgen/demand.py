"""Demand calculation and consumption modeling."""

from typing import Any, List, Dict
from decimal import Decimal
from .fantastical import with_fantastical_demand
from .models import Operator, DemandProfile, TechLevel
from .taxonomy import ResourceTaxonomy
import logging

logger = logging.getLogger(__name__)


class DemandCalculator:
    """Calculate resource demand based on population and technology level."""

    def __init__(self, taxonomy: ResourceTaxonomy, demand_profiles: List[DemandProfile]):
        """Initialize demand calculator.

        Args:
            taxonomy: Resource taxonomy for validation
            demand_profiles: Per-capita demand profiles by tech level
        """
        self.taxonomy = taxonomy
        self.profiles = {p.tech: p for p in demand_profiles}
        self._validate_profiles()
        logger.info(f"Initialized demand calculator with {len(self.profiles)} profiles")

    def _validate_profiles(self) -> None:
        """Validate that demand profiles reference valid resources."""
        missing_resources = set()

        for profile in self.profiles.values():
            for resource_id in profile.per_capita:
                if not self.taxonomy.get_resource(resource_id):
                    missing_resources.add(resource_id)

        if missing_resources:
            logger.warning(f"Demand profiles reference unknown resources: {missing_resources}")

    def calculate_operator_demand(self, operator: Operator) -> Dict[str, Decimal]:
        """Calculate total demand for a single operator.

        Args:
            operator: Economic operator

        Returns:
            Dictionary mapping resource_id to total demand quantity
        """
        if operator.population <= 0:
            return {}

        # Get base per-capita demand for this tech level
        profile = self.profiles.get(operator.tech)
        if not profile:
            logger.warning(f"No demand profile for tech level {operator.tech}")
            return {}

        # Calculate base demand
        base_demand = {}
        population = Decimal(str(operator.population))

        for resource_id, per_capita in profile.per_capita.items():
            base_demand[resource_id] = per_capita * population

        # Apply modifiers
        modified_demand = self._apply_demand_modifiers(base_demand, operator)

        # Filter out zero demands
        return {k: v for k, v in modified_demand.items() if v > 0}

    def _apply_demand_modifiers(
        self, base_demand: Dict[str, Decimal], operator: Operator
    ) -> Dict[str, Decimal]:
        """Apply various modifiers to base demand.

        Args:
            base_demand: Base per-capita demand scaled by population
            operator: Economic operator

        Returns:
            Modified demand dictionary
        """
        modified = base_demand.copy()

        # Infrastructure modifiers
        modified = self._apply_infrastructure_modifiers(modified, operator)

        # Cultural modifiers
        modified = self._apply_cultural_modifiers(modified, operator)

        # Wealth modifiers (based on infrastructure and population)
        modified = self._apply_wealth_modifiers(modified, operator)

        # Geographic modifiers
        modified = self._apply_geographic_modifiers(modified, operator)

        return modified

    def _apply_infrastructure_modifiers(
        self, demand: Dict[str, Decimal], operator: Operator
    ) -> Dict[str, Decimal]:
        """Apply infrastructure-based demand modifiers.

        Args:
            demand: Current demand dictionary
            operator: Economic operator

        Returns:
            Modified demand dictionary
        """
        modified = demand.copy()

        # Plaza increases demand for trade goods and luxury items
        if operator.plaza:
            for resource_id in ["textiles", "jewelry", "tools"]:
                if resource_id in modified:
                    modified[resource_id] *= Decimal("1.3")

        # Temple increases demand for luxury and ceremonial goods
        if operator.temple:
            for resource_id in ["jewelry", "textiles", "precious-metals"]:
                if resource_id in modified:
                    modified[resource_id] *= Decimal("1.5")

        # Port increases demand for preserved foods and trade goods
        if operator.port:
            for resource_id in ["fish", "salt", "textiles", "tools"]:
                if resource_id in modified:
                    modified[resource_id] *= Decimal("1.2")

        # Citadel increases demand for garrison supplies
        if operator.citadel:
            for resource_id in ["iron-ore", "food"]:
                if resource_id in modified:
                    modified[resource_id] *= Decimal("1.4")

        # Walls increase general security-related demand
        if operator.walls:
            for resource_id in ["tools", "stone"]:
                if resource_id in modified:
                    modified[resource_id] *= Decimal("1.1")

        return modified

    def _apply_cultural_modifiers(
        self, demand: Dict[str, Decimal], operator: Operator
    ) -> Dict[str, Decimal]:
        """Apply culture-based demand modifiers.

        Args:
            demand: Current demand dictionary
            operator: Economic operator

        Returns:
            Modified demand dictionary
        """
        modified = demand.copy()

        # Extract culture from tags
        culture_tags = [tag for tag in operator.tags if tag.startswith("culture_")]

        for culture_tag in culture_tags:
            culture = culture_tag.replace("culture_", "")

            if culture == "noon":
                # Noon culture values agriculture and textiles
                for resource_id in ["food", "textiles"]:
                    if resource_id in modified:
                        modified[resource_id] *= Decimal("1.2")

            elif culture == "night":
                # Night culture values craftsmanship
                for resource_id in ["tools", "jewelry"]:
                    if resource_id in modified:
                        modified[resource_id] *= Decimal("1.2")

            elif culture == "dawn":
                # Dawn culture values trade and mobility
                for resource_id in ["tools", "textiles", "food"]:
                    if resource_id in modified:
                        modified[resource_id] *= Decimal("1.1")

            elif culture == "day":
                # Day culture values stability and luxury
                for resource_id in ["jewelry", "textiles", "tools"]:
                    if resource_id in modified:
                        modified[resource_id] *= Decimal("1.15")

            elif culture == "drifters":
                # Drifters have lower overall demand (nomadic lifestyle)
                for resource_id in modified:
                    modified[resource_id] *= Decimal("0.8")

            elif culture == "wildlands":
                # Wildlands culture has different resource preferences
                for resource_id in ["food", "tools"]:
                    if resource_id in modified:
                        modified[resource_id] *= Decimal("1.1")
                for resource_id in ["jewelry", "luxury"]:
                    if resource_id in modified:
                        modified[resource_id] *= Decimal("0.7")

        return modified

    def _apply_wealth_modifiers(
        self, demand: Dict[str, Decimal], operator: Operator
    ) -> Dict[str, Decimal]:
        """Apply wealth-based demand modifiers.

        Args:
            demand: Current demand dictionary
            operator: Economic operator

        Returns:
            Modified demand dictionary
        """
        modified = demand.copy()

        # Calculate wealth indicator based on population and infrastructure
        wealth_score = Decimal("1.0")

        # Population contributes to wealth (economies of scale)
        if operator.population > 20000:
            wealth_score += Decimal("0.3")
        elif operator.population > 10000:
            wealth_score += Decimal("0.2")
        elif operator.population > 5000:
            wealth_score += Decimal("0.1")

        # Infrastructure contributes to wealth
        infrastructure_count = sum(
            [operator.plaza, operator.citadel, operator.temple, operator.port, operator.walls]
        )
        wealth_score += Decimal(str(infrastructure_count)) * Decimal("0.1")

        # Capital city bonus
        if operator.capital:
            wealth_score += Decimal("0.2")

        # Shanty town penalty
        if operator.shanty_town:
            wealth_score -= Decimal("0.3")

        # Apply wealth effects
        if wealth_score > Decimal("1.2"):
            # Wealthy cities demand more luxury goods
            for resource_id in ["jewelry", "textiles", "luxury", "machinery"]:
                if resource_id in modified:
                    modified[resource_id] *= wealth_score

        elif wealth_score < Decimal("0.8"):
            # Poor cities focus on essentials
            essentials = ["food", "tools", "basic-materials"]
            for resource_id in list(modified.keys()):
                if resource_id not in essentials:
                    modified[resource_id] *= wealth_score

        return modified

    def _apply_geographic_modifiers(
        self, demand: Dict[str, Decimal], operator: Operator
    ) -> Dict[str, Decimal]:
        """Apply geographic and climate-based modifiers.

        Args:
            demand: Current demand dictionary
            operator: Economic operator

        Returns:
            Modified demand dictionary
        """
        modified = demand.copy()

        # Port cities have different food preferences
        if operator.port:
            if "fish" in modified and "food" in modified:
                # Substitute some general food demand with fish
                fish_increase = modified["food"] * Decimal("0.3")
                modified["fish"] += fish_increase
                modified["food"] *= Decimal("0.8")

        # Mountain/elevated cities (inferred from mining endowments)
        if "mining_potential" in operator.endowments:
            # Higher demand for tools and equipment
            for resource_id in ["tools", "machinery"]:
                if resource_id in modified:
                    modified[resource_id] *= Decimal("1.2")

        # Forest regions (inferred from forestry endowments)
        if "forestry" in operator.endowments:
            # Higher demand for wood products, lower for textiles
            if "wood" in modified:
                modified["wood"] *= Decimal("1.3")
            if "textiles" in modified:
                modified["textiles"] *= Decimal("0.9")

        return modified

    def calculate_all_demand(self, operators: List[Operator]) -> Dict[str, Dict[str, Decimal]]:
        """Calculate demand for all operators.

        Args:
            operators: List of economic operators

        Returns:
            Dictionary mapping operator_id to resource demands
        """
        logger.info(f"Calculating demand for {len(operators)} operators")

        all_demand = {}
        for operator in operators:
            demand = self.calculate_operator_demand(operator)
            if demand:  # Only include operators with non-zero demand
                all_demand[operator.operator_id] = demand

        total_resources = sum(len(d) for d in all_demand.values())
        logger.info(
            f"Calculated demand for {len(all_demand)} operators, {total_resources} resource entries"
        )

        return all_demand

    def get_demand_summary(self, demand_dict: Dict[str, Dict[str, Decimal]]) -> Dict[str, Any]:
        """Get summary statistics about demand calculations.

        Args:
            demand_dict: Demand dictionary from calculate_all_demand

        Returns:
            Dictionary with demand statistics
        """
        if not demand_dict:
            return {"total_demand_entries": 0}

        # Aggregate demand by resource
        resource_totals: Dict[str, Decimal] = {}
        for operator_demand in demand_dict.values():
            for resource_id, quantity in operator_demand.items():
                resource_totals[resource_id] = (
                    resource_totals.get(resource_id, Decimal("0")) + quantity
                )

        total_entries = sum(len(d) for d in demand_dict.values())
        operators_with_demand = len(demand_dict)

        return {
            "total_demand_entries": total_entries,
            "operators_with_demand": operators_with_demand,
            "unique_resources_demanded": len(resource_totals),
            "avg_resources_per_operator": total_entries / operators_with_demand
            if operators_with_demand > 0
            else 0,
            "top_demanded_resources": sorted(
                [(k, float(v)) for k, v in resource_totals.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:5],
            "total_demand_volume": float(sum(resource_totals.values())),
        }


def create_default_demand_profiles() -> List[DemandProfile]:
    """Create default demand profiles for testing and examples.

    Returns:
        List of DemandProfile instances for each tech level
    """
    profiles: List[DemandProfile] = [
        DemandProfile(
            tech=TechLevel.TRIBAL,
            per_capita={
                "food": Decimal("2.5"),
                "wood": Decimal("1.0"),
                "stone": Decimal("0.5"),
                "tools": Decimal("0.2"),
                "fish": Decimal("0.8"),
            },
        ),
        DemandProfile(
            tech=TechLevel.MEDIEVAL,
            per_capita={
                "food": Decimal("2.0"),
                "wood": Decimal("0.8"),
                "stone": Decimal("0.3"),
                "iron-ore": Decimal("0.5"),
                "tools": Decimal("0.4"),
                "textiles": Decimal("0.6"),
                "fish": Decimal("0.5"),
                "jewelry": Decimal("0.1"),
            },
        ),
        DemandProfile(
            tech=TechLevel.INDUSTRIAL,
            per_capita={
                "food": Decimal("1.8"),
                "wood": Decimal("0.5"),
                "stone": Decimal("0.2"),
                "iron-ore": Decimal("0.8"),
                "steel": Decimal("0.4"),
                "tools": Decimal("0.6"),
                "textiles": Decimal("1.0"),
                "machinery": Decimal("0.3"),
                "fish": Decimal("0.4"),
                "jewelry": Decimal("0.2"),
            },
        ),
    ]

    return with_fantastical_demand(profiles)


# Export main classes and functions
__all__ = ["DemandCalculator", "create_default_demand_profiles"]
