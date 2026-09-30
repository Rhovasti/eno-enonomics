"""Price discovery and market dynamics."""

from typing import Dict, List
from decimal import Decimal
from .models import Operator, SimulationConfig, TechLevel
from .taxonomy import ResourceTaxonomy
from .util import clamp
import logging

logger = logging.getLogger(__name__)

# Bounds on local supply/demand ratio: 5% self-sufficiency to 20x oversupply
MIN_SUPPLY_RATIO = Decimal("0.05")
MAX_SUPPLY_RATIO = Decimal("20")


class PriceCalculator:
    """Calculate resource prices based on supply, demand, and market dynamics."""
    
    def __init__(self, taxonomy: ResourceTaxonomy, config: SimulationConfig):
        """Initialize price calculator.
        
        Args:
            taxonomy: Resource taxonomy for base prices
            config: Simulation configuration
        """
        self.taxonomy = taxonomy
        self.config = config
        logger.info("Initialized price calculator")
    
    def calculate_prices(
        self,
        operators: List[Operator],
        supply: Dict[str, Dict[str, Decimal]],  # operator_id -> resource_id -> quantity
        demand: Dict[str, Dict[str, Decimal]]   # operator_id -> resource_id -> quantity
    ) -> Dict[str, Dict[str, Decimal]]:  # operator_id -> resource_id -> price
        """Calculate market prices for all operators and resources.
        
        Args:
            operators: List of economic operators
            supply: Supply quantities by operator and resource
            demand: Demand quantities by operator and resource
            
        Returns:
            Calculated prices by operator and resource
        """
        logger.info(f"Calculating prices for {len(operators)} operators")
        
        # Calculate regional supply/demand ratios
        regional_ratios = self._calculate_regional_ratios(supply, demand)
        
        # Calculate base prices adjusted for scarcity/abundance
        prices = {}
        
        for operator in operators:
            operator_prices = self._calculate_operator_prices(
                operator, supply.get(operator.operator_id, {}),
                demand.get(operator.operator_id, {}), regional_ratios
            )
            if operator_prices:
                prices[operator.operator_id] = operator_prices
        
        logger.info(f"Calculated prices for {len(prices)} operators")
        return prices
    
    def _calculate_regional_ratios(
        self,
        supply: Dict[str, Dict[str, Decimal]],
        demand: Dict[str, Dict[str, Decimal]]
    ) -> Dict[str, Decimal]:
        """Calculate regional supply/demand ratios for each resource.
        
        Args:
            supply: Supply quantities by operator and resource
            demand: Demand quantities by operator and resource
            
        Returns:
            Dictionary mapping resource_id to supply/demand ratio
        """
        # Aggregate regional totals
        regional_supply = {}
        regional_demand = {}
        
        for operator_supply in supply.values():
            for resource_id, quantity in operator_supply.items():
                regional_supply[resource_id] = regional_supply.get(resource_id, Decimal("0")) + quantity
        
        for operator_demand in demand.values():
            for resource_id, quantity in operator_demand.items():
                regional_demand[resource_id] = regional_demand.get(resource_id, Decimal("0")) + quantity
        
        # Calculate ratios
        ratios = {}
        all_resources = set(regional_supply.keys()) | set(regional_demand.keys())
        
        for resource_id in all_resources:
            supply_qty = regional_supply.get(resource_id, Decimal("0"))
            demand_qty = regional_demand.get(resource_id, Decimal("0"))
            
            # Calculate ratio (>1 = surplus, <1 = shortage)
            if demand_qty > 0:
                ratios[resource_id] = supply_qty / demand_qty
            elif supply_qty > 0:
                ratios[resource_id] = Decimal("10.0")  # Large surplus
            else:
                ratios[resource_id] = Decimal("1.0")  # Balanced (no supply or demand)
        
        return ratios
    
    def _calculate_operator_prices(
        self,
        operator: Operator,
        operator_supply: Dict[str, Decimal],
        operator_demand: Dict[str, Decimal],
        regional_ratios: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Calculate prices for a single operator.
        
        Args:
            operator: Economic operator
            operator_supply: Supply quantities for this operator
            operator_demand: Demand quantities for this operator
            regional_ratios: Regional supply/demand ratios
            
        Returns:
            Dictionary mapping resource_id to price
        """
        prices = {}
        
        # Get all resources this operator deals with
        # Reason: sorted so output order does not depend on per-process string hashing
        all_resources = sorted(set(operator_supply.keys()) | set(operator_demand.keys()))
        
        for resource_id in all_resources:
            base_price = self.taxonomy.get_base_price(resource_id)
            if base_price <= 0:
                continue  # Skip unknown resources
            
            # Calculate local supply/demand ratio
            local_supply = operator_supply.get(resource_id, Decimal("0"))
            local_demand = operator_demand.get(resource_id, Decimal("0"))
            
            # Start with base price
            price = base_price
            
            # Apply scarcity multiplier if enabled
            if self.config.scarcity_multiplier:
                price = self._apply_scarcity_adjustment(
                    price, local_supply, local_demand, regional_ratios.get(resource_id, Decimal("1"))
                )
            
            # Apply operator-specific modifiers
            price = self._apply_operator_modifiers(price, operator, resource_id)
            
            # Apply bounds
            min_price = base_price * Decimal("0.1")  # Min 10% of base price
            max_price = base_price * Decimal("10.0")  # Max 1000% of base price
            price = clamp(price, min_price, max_price)
            
            prices[resource_id] = price
        
        return prices
    
    def _apply_scarcity_adjustment(
        self,
        base_price: Decimal,
        local_supply: Decimal,
        local_demand: Decimal,
        regional_ratio: Decimal
    ) -> Decimal:
        """Apply a constant-elasticity scarcity adjustment.

        The local multiplier is (demand / supply) ** (1 / price_elasticity): a smooth,
        monotonic curve where higher elasticity means flatter prices. The supply/demand
        ratio is bounded so that zero supply or zero demand gives a finite multiplier.

        Args:
            base_price: Base resource price
            local_supply: Local supply quantity
            local_demand: Local demand quantity
            regional_ratio: Regional supply/demand ratio

        Returns:
            Adjusted price
        """
        if local_demand > 0:
            local_ratio = local_supply / local_demand
        else:
            local_ratio = MAX_SUPPLY_RATIO if local_supply > 0 else Decimal("1")
        local_ratio = clamp(local_ratio, MIN_SUPPLY_RATIO, MAX_SUPPLY_RATIO)

        exponent = Decimal("1") / self.config.price_elasticity
        scarcity_multiplier = (Decimal("1") / local_ratio) ** exponent

        # Regional influence (weaker effect)
        if regional_ratio < Decimal("0.7"):
            regional_multiplier = Decimal("1.2")
        elif regional_ratio > Decimal("1.5"):
            regional_multiplier = Decimal("0.9")
        else:
            regional_multiplier = Decimal("1.0")

        return base_price * scarcity_multiplier * regional_multiplier

    def _apply_operator_modifiers(
        self,
        price: Decimal,
        operator: Operator,
        resource_id: str
    ) -> Decimal:
        """Apply operator-specific price modifiers.
        
        Args:
            price: Current price
            operator: Economic operator
            resource_id: Resource identifier
            
        Returns:
            Modified price
        """
        modified_price = price
        
        # Port cities have better access to trade goods
        if operator.port and resource_id in ["fish", "textiles", "exotic-goods"]:
            modified_price *= Decimal("0.9")  # 10% cheaper due to direct access
        
        # Plaza/market cities have better price discovery
        if operator.plaza:
            modified_price *= Decimal("0.95")  # 5% efficiency gain
        
        # Capital cities have price premiums due to demand
        if operator.capital:
            modified_price *= Decimal("1.1")  # 10% premium
        
        # Remote locations have higher prices due to transport costs
        # (This is a simplified proxy - in reality we'd calculate actual remoteness)
        if not operator.port and operator.population < 5000:
            modified_price *= Decimal("1.15")  # 15% remoteness penalty
        
        # Technology level affects pricing efficiency
        if operator.tech == TechLevel.TRIBAL:
            modified_price *= Decimal("1.05")  # Less efficient markets
        elif operator.tech == TechLevel.INDUSTRIAL:
            modified_price *= Decimal("0.98")  # More efficient markets
        
        # Cultural modifiers
        culture_tags = [tag for tag in operator.tags if tag.startswith("culture_")]
        
        for culture_tag in culture_tags:
            culture = culture_tag.replace("culture_", "")
            
            if culture == "noon" and resource_id in ["food", "agriculture"]:
                modified_price *= Decimal("0.92")  # Agricultural specialization
            elif culture == "night" and resource_id in ["crafts", "tools", "weapons"]:
                modified_price *= Decimal("0.95")  # Crafting specialization
            elif culture == "dawn" and resource_id in ["trade-goods"]:
                modified_price *= Decimal("0.90")  # Trade specialization
        
        # Shanty towns have inflated prices due to poor infrastructure
        if operator.shanty_town:
            modified_price *= Decimal("1.2")  # 20% penalty
        
        return modified_price
    
    def get_price_statistics(
        self,
        prices: Dict[str, Dict[str, Decimal]]
    ) -> Dict[str, any]:
        """Calculate price statistics across all operators.
        
        Args:
            prices: Price dictionary from calculate_prices
            
        Returns:
            Dictionary with price statistics
        """
        if not prices:
            return {"total_price_entries": 0}
        
        # Collect all prices by resource
        resource_prices = {}
        total_entries = 0
        
        for operator_prices in prices.values():
            for resource_id, price in operator_prices.items():
                if resource_id not in resource_prices:
                    resource_prices[resource_id] = []
                resource_prices[resource_id].append(price)
                total_entries += 1
        
        # Calculate statistics
        price_stats = {}
        for resource_id, price_list in resource_prices.items():
            if price_list:
                price_stats[resource_id] = {
                    "min": float(min(price_list)),
                    "max": float(max(price_list)),
                    "avg": float(sum(price_list) / len(price_list)),
                    "markets": len(price_list)
                }
        
        return {
            "total_price_entries": total_entries,
            "unique_resources_priced": len(resource_prices),
            "operators_with_prices": len(prices),
            "avg_resources_per_operator": total_entries / len(prices) if prices else 0,
            "resource_price_stats": price_stats,
            "price_volatility": self._calculate_price_volatility(resource_prices)
        }
    
    def _calculate_price_volatility(
        self,
        resource_prices: Dict[str, List[Decimal]]
    ) -> Dict[str, float]:
        """Calculate price volatility (coefficient of variation) for each resource.
        
        Args:
            resource_prices: Prices by resource across all operators
            
        Returns:
            Volatility metrics by resource
        """
        volatility = {}
        
        for resource_id, price_list in resource_prices.items():
            if len(price_list) < 2:
                volatility[resource_id] = 0.0
                continue
            
            # Calculate coefficient of variation (std dev / mean)
            prices_float = [float(p) for p in price_list]
            mean_price = sum(prices_float) / len(prices_float)
            
            if mean_price == 0:
                volatility[resource_id] = 0.0
                continue
            
            variance = sum((p - mean_price) ** 2 for p in prices_float) / len(prices_float)
            std_dev = variance ** 0.5
            
            volatility[resource_id] = std_dev / mean_price
        
        return volatility


# Export main class
__all__ = ["PriceCalculator"]