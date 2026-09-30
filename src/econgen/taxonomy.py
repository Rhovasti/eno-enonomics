"""Resource taxonomy and classification system."""

from typing import Any, List, Dict, Optional
from decimal import Decimal
from .fantastical import fantastical_resources
from .models import Resource, TechLevel
import logging

logger = logging.getLogger(__name__)


class ResourceTaxonomy:
    """Manages the hierarchy and relationships of economic resources."""

    def __init__(self, resources: List[Resource]):
        """Initialize resource taxonomy.

        Args:
            resources: List of Resource definitions
        """
        self.resources = {r.resource_id: r for r in resources}
        self._validate_consistency()
        logger.info(f"Initialized taxonomy with {len(self.resources)} resources")

    def _validate_consistency(self) -> None:
        """Validate that resource taxonomy is internally consistent."""
        # Check for duplicate IDs (should be prevented by dict, but good to verify)
        resource_ids = [r.resource_id for r in self.resources.values()]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Duplicate resource IDs detected")

        # Validate tier ordering makes sense with tech requirements
        for resource in self.resources.values():
            # Higher tiers should generally require higher tech levels
            if resource.tier >= 2 and resource.tech_min == TechLevel.TRIBAL:
                logger.warning(
                    f"Resource {resource.resource_id} has high tier ({resource.tier}) "
                    f"but low tech requirement ({resource.tech_min})"
                )

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get resource by ID.

        Args:
            resource_id: Resource identifier

        Returns:
            Resource instance or None if not found
        """
        return self.resources.get(resource_id)

    def get_resources_by_tier(self, tier: int) -> List[Resource]:
        """Get all resources of specified tier.

        Args:
            tier: Resource tier (0=raw, 1=refined, 2=advanced, 3=luxury)

        Returns:
            List of resources in tier
        """
        return [r for r in self.resources.values() if r.tier == tier]

    def get_resources_by_tech(self, tech_level: TechLevel) -> List[Resource]:
        """Get all resources available at specified tech level.

        Args:
            tech_level: Technology level

        Returns:
            List of resources available at this tech level or lower
        """
        return [
            r for r in self.resources.values() if TechLevel(r.tech_min) <= TechLevel(tech_level)
        ]

    def get_raw_materials(self) -> List[Resource]:
        """Get all raw materials (tier 0)."""
        return self.get_resources_by_tier(0)

    def get_refined_goods(self) -> List[Resource]:
        """Get all refined goods (tier 1)."""
        return self.get_resources_by_tier(1)

    def get_advanced_goods(self) -> List[Resource]:
        """Get all advanced goods (tier 2)."""
        return self.get_resources_by_tier(2)

    def get_luxury_goods(self) -> List[Resource]:
        """Get all luxury goods (tier 3)."""
        return self.get_resources_by_tier(3)

    def get_transportable_resources(self) -> List[Resource]:
        """Get all resources that can be traded."""
        return [r for r in self.resources.values() if r.transportable]

    def get_perishable_resources(self) -> List[Resource]:
        """Get all resources that are perishable."""
        return [r for r in self.resources.values() if r.perishable]

    def get_base_price(self, resource_id: str) -> Decimal:
        """Get base price for resource.

        Args:
            resource_id: Resource identifier

        Returns:
            Base price or zero if resource not found
        """
        resource = self.get_resource(resource_id)
        return resource.base_price if resource else Decimal("0")

    def is_available_at_tech(self, resource_id: str, tech_level: TechLevel) -> bool:
        """Check if resource is available at given tech level.

        Args:
            resource_id: Resource identifier
            tech_level: Technology level to check

        Returns:
            True if resource is available at this tech level
        """
        resource = self.get_resource(resource_id)
        return resource is not None and TechLevel(resource.tech_min) <= TechLevel(tech_level)

    def get_technology_gaps(self) -> Dict[TechLevel, List[Resource]]:
        """Get resources grouped by minimum technology level.

        Returns:
            Dictionary mapping tech levels to available resources
        """
        gaps: Dict[TechLevel, List[Resource]] = {level: [] for level in TechLevel}
        for resource in self.resources.values():
            gaps[resource.tech_min].append(resource)
        return gaps

    def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary statistics about the resource taxonomy.

        Returns:
            Dictionary with summary statistics
        """
        total = len(self.resources)
        by_tier = {tier: len(self.get_resources_by_tier(tier)) for tier in range(4)}
        by_tech = {str(level): len(self.get_resources_by_tech(level)) for level in TechLevel}
        transportable = len(self.get_transportable_resources())
        perishable = len(self.get_perishable_resources())

        return {
            "total_resources": total,
            "by_tier": by_tier,
            "by_tech_level": by_tech,
            "transportable": transportable,
            "perishable": perishable,
            "average_base_price": float(sum(r.base_price for r in self.resources.values()) / total)
            if total > 0
            else 0,
        }


def create_default_taxonomy() -> ResourceTaxonomy:
    """Create a default resource taxonomy for testing and examples.

    Returns:
        ResourceTaxonomy with basic resource set
    """
    default_resources = [
        # Tier 0: Raw Materials
        Resource(
            resource_id="wood",
            name="Wood",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("1.0"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="stone",
            name="Stone",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("0.8"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="iron-ore",
            name="Iron Ore",
            tier=0,
            tech_min=TechLevel.MEDIEVAL,
            base_price=Decimal("3.0"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="food",
            name="Food",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("2.0"),
            transportable=True,
            perishable=True,
        ),
        Resource(
            resource_id="fish",
            name="Fish",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("2.5"),
            transportable=True,
            perishable=True,
        ),
        Resource(
            resource_id="coal",
            name="Coal",
            tier=0,
            tech_min=TechLevel.MEDIEVAL,
            base_price=Decimal("1.5"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="precious-metals",
            name="Precious Metals",
            tier=0,
            tech_min=TechLevel.MEDIEVAL,
            base_price=Decimal("15.0"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="gems",
            name="Gems",
            tier=0,
            tech_min=TechLevel.MEDIEVAL,
            base_price=Decimal("25.0"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="fiber",
            name="Fiber",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("1.2"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="seed",
            name="Seed",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("0.5"),
            transportable=True,
            perishable=True,
        ),
        # Tier 1: Refined Goods
        Resource(
            resource_id="tools",
            name="Tools",
            tier=1,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("5.0"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="textiles",
            name="Textiles",
            tier=1,
            tech_min=TechLevel.MEDIEVAL,
            base_price=Decimal("4.0"),
            transportable=True,
            perishable=False,
        ),
        # Tier 2: Advanced Goods
        Resource(
            resource_id="steel",
            name="Steel",
            tier=2,
            tech_min=TechLevel.INDUSTRIAL,
            base_price=Decimal("12.0"),
            transportable=True,
            perishable=False,
        ),
        Resource(
            resource_id="machinery",
            name="Machinery",
            tier=2,
            tech_min=TechLevel.INDUSTRIAL,
            base_price=Decimal("25.0"),
            transportable=True,
            perishable=False,
        ),
        # Byproducts
        Resource(
            resource_id="slag",
            name="Slag",
            tier=2,
            tech_min=TechLevel.INDUSTRIAL,
            base_price=Decimal("0.2"),
            transportable=True,
            perishable=False,
        ),
        # Tier 3: Luxury Goods
        Resource(
            resource_id="jewelry",
            name="Jewelry",
            tier=3,
            tech_min=TechLevel.MEDIEVAL,
            base_price=Decimal("50.0"),
            transportable=True,
            perishable=False,
        ),
    ]

    default_resources += fantastical_resources()

    return ResourceTaxonomy(default_resources)


# Export main classes and functions
__all__ = ["ResourceTaxonomy", "create_default_taxonomy"]
