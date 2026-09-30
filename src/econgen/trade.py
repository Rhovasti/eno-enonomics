"""Trade network and flow calculation."""

from typing import List, Dict, Tuple, Any
from decimal import Decimal
import numpy as np
from scipy.spatial import KDTree

from .models import Operator, TradeLink, SimulationConfig
from .util import calculate_great_circle_distance
import logging

logger = logging.getLogger(__name__)


class TradeNetwork:
    """Build and solve trade network flows between operators."""

    def __init__(self, operators: List[Operator], config: SimulationConfig):
        """Initialize trade network.

        Args:
            operators: List of economic operators
            config: Simulation configuration
        """
        self.operators = {op.operator_id: op for op in operators}
        self.config = config
        self._build_spatial_index()
        self._partner_cache: Dict[str, List[str]] = {}
        logger.info(f"Initialized trade network with {len(self.operators)} operators")

    def _build_spatial_index(self) -> None:
        """Build KDTree for efficient nearest-neighbor queries."""
        if not self.operators:
            logger.warning("No operators provided for spatial index")
            self.kdtree = None
            self.op_ids = []
            return

        # Extract coordinates and operator IDs
        coords = []
        op_ids = []

        for op in self.operators.values():
            coords.append(op.coord)
            op_ids.append(op.operator_id)

        self.kdtree = KDTree(coords)
        self.op_ids = op_ids
        logger.info(f"Built spatial index with {len(coords)} operators")

    def find_trade_partners(self, operator_id: str) -> List[str]:
        """Find potential trade partners within radius and neighbor limit.

        Args:
            operator_id: Source operator ID

        Returns:
            List of potential partner operator IDs
        """
        # Check cache first
        if operator_id in self._partner_cache:
            return self._partner_cache[operator_id]

        if not self.kdtree or operator_id not in self.operators:
            return []

        operator = self.operators[operator_id]

        # Convert radius from km to degrees (rough approximation)
        radius_deg = float(self.config.max_trade_radius_km) / 111.0

        # Verify operator exists in spatial index
        try:
            self.op_ids.index(operator_id)
        except ValueError:
            logger.warning(f"Operator {operator_id} not found in spatial index")
            return []

        # Query neighbors within radius
        max_neighbors = min(len(self.operators) - 1, self.config.max_trade_neighbors + 10)

        try:
            distances, indices = self.kdtree.query(
                operator.coord,
                k=max_neighbors + 1,  # +1 to include self (which we'll filter out)
                distance_upper_bound=radius_deg,
            )
        except Exception as e:
            logger.error(f"KDTree query failed for {operator_id}: {e}")
            return []

        # Filter results
        partners = []
        for dist, idx in zip(distances, indices):
            # Skip invalid indices and self
            if idx >= len(self.op_ids) or self.op_ids[idx] == operator_id:
                continue

            # Skip infinite distances (outside radius)
            if np.isinf(dist):
                continue

            partner_id = self.op_ids[idx]
            partners.append(partner_id)

            # Limit to configured maximum
            if len(partners) >= self.config.max_trade_neighbors:
                break

        # Cache result
        self._partner_cache[operator_id] = partners
        return partners

    def calculate_distance(self, op1_id: str, op2_id: str) -> Decimal:
        """Calculate distance between two operators.

        Args:
            op1_id: First operator ID
            op2_id: Second operator ID

        Returns:
            Distance in kilometers
        """
        if op1_id not in self.operators or op2_id not in self.operators:
            return Decimal("999999")  # Very large distance for invalid operators

        op1 = self.operators[op1_id]
        op2 = self.operators[op2_id]

        return calculate_great_circle_distance(op1.coord, op2.coord)

    def solve_trade_flows(
        self,
        supply: Dict[str, Dict[str, Decimal]],  # operator_id -> resource_id -> surplus_qty
        demand: Dict[str, Dict[str, Decimal]],  # operator_id -> resource_id -> needed_qty
        prices: Dict[str, Dict[str, Decimal]],  # operator_id -> resource_id -> price
    ) -> List[TradeLink]:
        """Solve trade flows using greedy profit maximization algorithm.

        Args:
            supply: Supply quantities by operator and resource
            demand: Demand quantities by operator and resource
            prices: Prices by operator and resource

        Returns:
            List of profitable trade links
        """
        logger.info("Solving trade flows with greedy profit maximization")

        # Reason: operators consume their own output first; only the net surplus is
        # exportable and only the net deficit needs importing.
        remaining_supply = self._net_positions(supply, demand)
        remaining_demand = self._net_positions(demand, supply)

        # Generate all possible trade opportunities
        opportunities = self._generate_trade_opportunities(
            remaining_supply, remaining_demand, prices
        )

        logger.info(f"Generated {len(opportunities)} potential trade opportunities")

        # Sort by profitability (descending)
        opportunities.sort(key=lambda x: x[0], reverse=True)

        # Greedily execute profitable trades
        trade_links = self._execute_trades(
            opportunities, remaining_supply, remaining_demand, prices
        )

        logger.info(f"Created {len(trade_links)} trade links")
        return trade_links

    def _generate_trade_opportunities(
        self,
        supply: Dict[str, Dict[str, Decimal]],
        demand: Dict[str, Dict[str, Decimal]],
        prices: Dict[str, Dict[str, Decimal]],
    ) -> List[Tuple[Decimal, str, str, str, Decimal]]:
        """Generate all potential trade opportunities.

        Returns:
            List of tuples: (profit_per_unit, source_id, dest_id, resource_id, distance)
        """
        opportunities = []

        for source_id in supply:
            # Get trade partners for this source
            partners = self.find_trade_partners(source_id)

            for dest_id in partners:
                if dest_id not in demand:
                    continue

                # Find common resources (source has surplus, dest has demand)
                source_resources = set(supply[source_id].keys())
                dest_resources = set(demand[dest_id].keys())
                # Reason: sorted so tie-breaking between equal-profit trades is reproducible
                common_resources = sorted(source_resources & dest_resources)

                for resource_id in common_resources:
                    # Check if both have positive quantities
                    supply_qty = supply[source_id].get(resource_id, Decimal("0"))
                    demand_qty = demand[dest_id].get(resource_id, Decimal("0"))

                    if supply_qty <= 0 or demand_qty <= 0:
                        continue

                    # Calculate profitability
                    source_price = prices.get(source_id, {}).get(resource_id, Decimal("1"))
                    dest_price = prices.get(dest_id, {}).get(resource_id, Decimal("1"))

                    distance = self.calculate_distance(source_id, dest_id)
                    transport_cost = distance * self.config.transport_cost_per_km

                    profit_per_unit = dest_price - source_price - transport_cost

                    # Only consider profitable trades
                    if profit_per_unit > 0:
                        opportunities.append(
                            (profit_per_unit, source_id, dest_id, resource_id, distance)
                        )

        return opportunities

    def _execute_trades(
        self,
        opportunities: List[Tuple[Decimal, str, str, str, Decimal]],
        remaining_supply: Dict[str, Dict[str, Decimal]],
        remaining_demand: Dict[str, Dict[str, Decimal]],
        prices: Dict[str, Dict[str, Decimal]],
    ) -> List[TradeLink]:
        """Execute trade opportunities in order of profitability.

        Args:
            opportunities: Sorted list of trade opportunities
            remaining_supply: Mutable supply tracking
            remaining_demand: Mutable demand tracking
            prices: Price information

        Returns:
            List of executed trade links
        """
        trade_links = []

        for profit, source_id, dest_id, resource_id, distance in opportunities:
            # Check if trade is still viable
            supply_available = remaining_supply.get(source_id, {}).get(resource_id, Decimal("0"))
            demand_needed = remaining_demand.get(dest_id, {}).get(resource_id, Decimal("0"))

            if supply_available <= 0 or demand_needed <= 0:
                continue

            # Determine trade quantity
            trade_qty = min(supply_available, demand_needed)

            # Respect minimum trade quantity
            if trade_qty < self.config.min_trade_quantity:
                continue

            # Create trade link
            transport_cost_total = distance * self.config.transport_cost_per_km

            link = TradeLink(
                source_id=source_id,
                dest_id=dest_id,
                resource_id=resource_id,
                quantity=trade_qty,
                distance_km=distance,
                transport_cost=transport_cost_total,
                price_source=prices.get(source_id, {}).get(resource_id, Decimal("1")),
                price_dest=prices.get(dest_id, {}).get(resource_id, Decimal("1")),
                profit_margin=profit * trade_qty,
            )

            trade_links.append(link)

            # Update remaining quantities
            remaining_supply[source_id][resource_id] -= trade_qty
            remaining_demand[dest_id][resource_id] -= trade_qty

            # Clean up zero quantities
            if remaining_supply[source_id][resource_id] <= 0:
                del remaining_supply[source_id][resource_id]
            if remaining_demand[dest_id][resource_id] <= 0:
                del remaining_demand[dest_id][resource_id]

        return trade_links

    def _net_positions(
        self,
        quantities: Dict[str, Dict[str, Decimal]],
        offsets: Dict[str, Dict[str, Decimal]],
    ) -> Dict[str, Dict[str, Decimal]]:
        """Return positive quantities left after subtracting each operator's offsets.

        Args:
            quantities: Quantities by operator and resource (e.g. supply)
            offsets: Quantities to subtract by operator and resource (e.g. own demand)

        Returns:
            Only the strictly positive remainders, by operator and resource
        """
        net: Dict[str, Dict[str, Decimal]] = {}
        for operator_id, resources in quantities.items():
            own = offsets.get(operator_id, {})
            positive = {
                resource_id: qty - own.get(resource_id, Decimal("0"))
                for resource_id, qty in resources.items()
                if qty > own.get(resource_id, Decimal("0"))
            }
            if positive:
                net[operator_id] = positive
        return net

    def _deep_copy_dict(self, d: Dict[str, Dict[str, Decimal]]) -> Dict[str, Dict[str, Decimal]]:
        """Create deep copy of nested dictionary."""
        return {k: {k2: v2 for k2, v2 in v.items()} for k, v in d.items()}

    def get_network_statistics(self, trade_links: List[TradeLink]) -> Dict[str, Any]:
        """Calculate network statistics from trade links.

        Args:
            trade_links: List of trade links

        Returns:
            Dictionary with network statistics
        """
        if not trade_links:
            return {
                "total_links": 0,
                "total_trade_volume": 0.0,
                "total_trade_value": 0.0,
                "average_distance": 0.0,
                "unique_traders": 0,
                "unique_resources_traded": 0,
            }

        total_volume = sum(link.quantity for link in trade_links)
        total_value = sum(link.quantity * link.price_source for link in trade_links)
        avg_distance = sum(link.distance_km for link in trade_links) / len(trade_links)

        traders = set()
        resources = set()

        for link in trade_links:
            traders.add(link.source_id)
            traders.add(link.dest_id)
            resources.add(link.resource_id)

        # Calculate profit statistics
        profitable_links = [link for link in trade_links if link.is_profitable]
        total_profit = sum(link.profit_margin for link in trade_links)

        return {
            "total_links": len(trade_links),
            "total_trade_volume": float(total_volume),
            "total_trade_value": float(total_value),
            "total_profit": float(total_profit),
            "average_distance": float(avg_distance),
            "max_distance": float(max(link.distance_km for link in trade_links)),
            "min_distance": float(min(link.distance_km for link in trade_links)),
            "unique_traders": len(traders),
            "unique_resources_traded": len(resources),
            "profitable_links": len(profitable_links),
            "profitability_rate": len(profitable_links) / len(trade_links) if trade_links else 0,
            "average_trade_size": float(total_volume / len(trade_links)) if trade_links else 0,
        }

    def get_operator_trade_summary(self, trade_links: List[TradeLink]) -> Dict[str, Dict[str, Any]]:
        """Get trade summary for each operator.

        Args:
            trade_links: List of trade links

        Returns:
            Dictionary mapping operator_id to trade statistics
        """
        summary: Dict[str, Dict[str, Any]] = {}

        # Initialize all operators
        for op_id in self.operators:
            summary[op_id] = {
                "exports": {},  # resource -> quantity
                "imports": {},  # resource -> quantity
                "export_value": Decimal("0"),
                "import_value": Decimal("0"),
                "trade_partners": set(),
                "trade_balance": Decimal("0"),
            }

        # Process trade links
        for link in trade_links:
            # Export (source)
            if link.source_id in summary:
                exports = summary[link.source_id]["exports"]
                exports[link.resource_id] = (
                    exports.get(link.resource_id, Decimal("0")) + link.quantity
                )

                export_value = link.quantity * link.price_source
                summary[link.source_id]["export_value"] += export_value
                summary[link.source_id]["trade_partners"].add(link.dest_id)
                summary[link.source_id]["trade_balance"] += export_value

            # Import (destination)
            if link.dest_id in summary:
                imports = summary[link.dest_id]["imports"]
                imports[link.resource_id] = (
                    imports.get(link.resource_id, Decimal("0")) + link.quantity
                )

                import_value = link.quantity * link.price_dest
                summary[link.dest_id]["import_value"] += import_value
                summary[link.dest_id]["trade_partners"].add(link.source_id)
                summary[link.dest_id]["trade_balance"] -= import_value

        # Convert sets to counts and Decimals to floats for JSON serialization
        for op_id in summary:
            summary[op_id]["trade_partners"] = len(summary[op_id]["trade_partners"])
            summary[op_id]["export_value"] = float(summary[op_id]["export_value"])
            summary[op_id]["import_value"] = float(summary[op_id]["import_value"])
            summary[op_id]["trade_balance"] = float(summary[op_id]["trade_balance"])

            # Convert Decimal quantities to float
            summary[op_id]["exports"] = {k: float(v) for k, v in summary[op_id]["exports"].items()}
            summary[op_id]["imports"] = {k: float(v) for k, v in summary[op_id]["imports"].items()}

        return summary

    def clear_cache(self) -> None:
        """Clear trade partner cache."""
        self._partner_cache.clear()
        logger.info("Cleared trade network cache")


# Export main class
__all__ = ["TradeNetwork"]
