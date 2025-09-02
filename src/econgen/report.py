"""Report generation for economic simulation results."""

from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime

from .models import Operator, TradeLink, Capacity, TechLevel
from .util import format_number
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate human-readable reports from simulation results."""
    
    def __init__(
        self,
        operators: List[Operator],
        trade_links: List[TradeLink],
        capacities: List[Capacity],
        prices: Optional[Dict[str, Dict[str, Decimal]]] = None,
        supply: Optional[Dict[str, Dict[str, Decimal]]] = None,
        demand: Optional[Dict[str, Dict[str, Decimal]]] = None
    ):
        """Initialize report generator.
        
        Args:
            operators: List of economic operators
            trade_links: List of trade links
            capacities: List of production capacities
            prices: Price information by operator and resource
            supply: Supply information by operator and resource
            demand: Demand information by operator and resource
        """
        self.operators = {op.operator_id: op for op in operators}
        self.trade_links = trade_links
        self.capacities = capacities
        self.prices = prices or {}
        self.supply = supply or {}
        self.demand = demand or {}
        
        logger.info(f"Initialized report generator with {len(operators)} operators, "
                   f"{len(trade_links)} trade links, {len(capacities)} capacities")
    
    def generate_full_report(self) -> str:
        """Generate comprehensive markdown report.
        
        Returns:
            Complete report as markdown string
        """
        logger.info("Generating full economic simulation report")
        
        sections = [
            self._generate_header(),
            self._generate_executive_summary(),
            self._generate_operator_overview(),
            self._generate_production_analysis(),
            self._generate_trade_analysis(),
            self._generate_market_analysis(),
            self._generate_regional_analysis(),
            self._generate_appendices()
        ]
        
        report = "\n\n".join(sections)
        logger.info("Report generation completed")
        return report
    
    def _generate_header(self) -> str:
        """Generate report header."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""# Economic Worldbuilding Analysis Report

**Generated:** {timestamp}  
**Simulation Framework:** Economic Worldbuilding Generator v0.1.0

---"""
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        total_operators = len(self.operators)
        total_trade_links = len(self.trade_links)
        total_capacities = len(self.capacities)
        
        # Calculate totals
        total_population = sum(op.population for op in self.operators.values())
        total_trade_volume = sum(link.quantity for link in self.trade_links)
        
        # Tech level distribution
        tech_dist = {}
        for op in self.operators.values():
            tech_dist[op.tech] = tech_dist.get(op.tech, 0) + 1
        
        # Infrastructure stats
        capitals = sum(1 for op in self.operators.values() if op.capital)
        ports = sum(1 for op in self.operators.values() if op.port)
        markets = sum(1 for op in self.operators.values() if op.plaza)
        
        return f"""## Executive Summary

### Overview
The economic simulation analyzed **{total_operators}** cities and settlements across a diverse technological landscape. The analysis reveals {total_trade_links} active trade routes moving {format_number(total_trade_volume)} units of goods, supported by {total_capacities} distinct production capabilities.

### Key Metrics
- **Total Population**: {total_population:,} inhabitants
- **Trade Volume**: {format_number(total_trade_volume)} units
- **Active Trade Routes**: {total_trade_links}
- **Production Capabilities**: {total_capacities}

### Technological Distribution
- **Tribal Era**: {tech_dist.get(TechLevel.TRIBAL, 0)} settlements
- **Medieval Era**: {tech_dist.get(TechLevel.MEDIEVAL, 0)} settlements  
- **Industrial Era**: {tech_dist.get(TechLevel.INDUSTRIAL, 0)} settlements

### Infrastructure
- **Capital Cities**: {capitals}
- **Port Cities**: {ports}
- **Market Towns**: {markets}"""
    
    def _generate_operator_overview(self) -> str:
        """Generate operator overview section."""
        # Sort operators by population
        sorted_ops = sorted(self.operators.values(), key=lambda x: x.population, reverse=True)
        
        # Top 10 largest cities
        top_cities = sorted_ops[:10]
        
        section = """## Settlement Overview

### Largest Cities by Population

| Rank | City | Population | Tech Level | Features |
|------|------|-----------|------------|----------|"""
        
        for i, op in enumerate(top_cities, 1):
            features = []
            if op.capital:
                features.append("Capital")
            if op.port:
                features.append("Port")
            if op.plaza:
                features.append("Market")
            if op.citadel:
                features.append("Fortress")
            if op.temple:
                features.append("Temple")
            
            features_str = ", ".join(features) if features else "None"
            
            section += f"""
| {i} | {op.name} | {op.population:,} | {str(op.tech).title()} | {features_str} |"""
        
        # Regional distribution
        section += "\n\n### Regional Distribution\n"
        
        # Group by culture (if available in tags)
        culture_groups = {}
        for op in self.operators.values():
            culture_tags = [tag for tag in op.tags if tag.startswith("culture_")]
            culture = culture_tags[0].replace("culture_", "").title() if culture_tags else "Unknown"
            
            if culture not in culture_groups:
                culture_groups[culture] = {"count": 0, "population": 0}
            
            culture_groups[culture]["count"] += 1
            culture_groups[culture]["population"] += op.population
        
        for culture, stats in sorted(culture_groups.items()):
            avg_pop = stats["population"] // stats["count"] if stats["count"] > 0 else 0
            section += f"- **{culture}**: {stats['count']} settlements, {stats['population']:,} total population (avg: {avg_pop:,})\n"
        
        return section
    
    def _generate_production_analysis(self) -> str:
        """Generate production capacity analysis."""
        if not self.capacities:
            return "## Production Analysis\n\n*No production capacity data available.*"
        
        # Group capacities by operator
        op_capacities = {}
        rule_totals = {}
        
        for cap in self.capacities:
            if cap.operator_id not in op_capacities:
                op_capacities[cap.operator_id] = []
            op_capacities[cap.operator_id].append(cap)
            
            rule_totals[cap.rule_id] = rule_totals.get(cap.rule_id, Decimal("0")) + cap.max_rate
        
        # Top production centers
        top_producers = sorted(
            [(op_id, caps) for op_id, caps in op_capacities.items()],
            key=lambda x: sum(c.max_rate for c in x[1]),
            reverse=True
        )[:10]
        
        section = """## Production Analysis

### Top Production Centers

| City | Total Capacity | Primary Industries | Tech Level |
|------|---------------|-------------------|------------|"""
        
        for op_id, caps in top_producers:
            op = self.operators.get(op_id)
            if not op:
                continue
            
            total_cap = sum(c.max_rate for c in caps)
            top_rules = sorted(caps, key=lambda x: x.max_rate, reverse=True)[:3]
            industries = ", ".join(rule.rule_id.replace("-", " ").title() for rule in top_rules)
            
            section += f"""
| {op.name} | {format_number(total_cap)} | {industries} | {str(op.tech).title()} |"""
        
        # Production by industry
        section += "\n\n### Production by Industry\n\n"
        
        sorted_rules = sorted(rule_totals.items(), key=lambda x: x[1], reverse=True)
        
        for rule_id, total_capacity in sorted_rules[:15]:  # Top 15 industries
            rule_name = rule_id.replace("-", " ").title()
            operators_count = sum(1 for cap in self.capacities if cap.rule_id == rule_id)
            
            section += f"- **{rule_name}**: {format_number(total_capacity)} total capacity across {operators_count} producers\n"
        
        return section
    
    def _generate_trade_analysis(self) -> str:
        """Generate trade network analysis."""
        if not self.trade_links:
            return "## Trade Analysis\n\n*No trade data available.*"
        
        # Trade statistics
        total_volume = sum(link.quantity for link in self.trade_links)
        avg_distance = sum(link.distance_km for link in self.trade_links) / len(self.trade_links)
        
        # Resource trade volumes
        resource_volumes = {}
        for link in self.trade_links:
            resource_volumes[link.resource_id] = resource_volumes.get(link.resource_id, Decimal("0")) + link.quantity
        
        # Major trade routes (by volume)
        trade_routes = {}
        for link in self.trade_links:
            route_key = f"{link.source_id}-{link.dest_id}"
            if route_key not in trade_routes:
                trade_routes[route_key] = {"volume": Decimal("0"), "resources": set(), "distance": link.distance_km}
            trade_routes[route_key]["volume"] += link.quantity
            trade_routes[route_key]["resources"].add(link.resource_id)
        
        top_routes = sorted(trade_routes.items(), key=lambda x: x[1]["volume"], reverse=True)[:10]
        
        section = f"""## Trade Analysis

### Trade Network Overview
- **Total Trade Volume**: {format_number(total_volume)} units
- **Active Trade Routes**: {len(self.trade_links)}
- **Average Trade Distance**: {format_number(avg_distance)} km
- **Unique Trading Partners**: {len(set(link.source_id for link in self.trade_links) | set(link.dest_id for link in self.trade_links))}

### Most Traded Resources

| Resource | Total Volume | Trade Routes |
|----------|-------------|--------------|"""
        
        sorted_resources = sorted(resource_volumes.items(), key=lambda x: x[1], reverse=True)
        
        for resource_id, volume in sorted_resources[:10]:
            resource_name = resource_id.replace("-", " ").title()
            route_count = sum(1 for link in self.trade_links if link.resource_id == resource_id)
            
            section += f"""
| {resource_name} | {format_number(volume)} | {route_count} |"""
        
        section += "\n\n### Major Trade Routes\n\n"
        
        for route_key, route_data in top_routes:
            source_id, dest_id = route_key.split("-", 1)
            source_name = self.operators.get(source_id, type('obj', (object,), {'name': source_id})).name
            dest_name = self.operators.get(dest_id, type('obj', (object,), {'name': dest_id})).name
            
            resources_str = ", ".join(sorted(route_data["resources"]))[:60] + ("..." if len(", ".join(route_data["resources"])) > 60 else "")
            
            section += f"- **{source_name} → {dest_name}**: {format_number(route_data['volume'])} units, {format_number(route_data['distance'])} km ({resources_str})\n"
        
        return section
    
    def _generate_market_analysis(self) -> str:
        """Generate market and pricing analysis."""
        if not self.prices:
            return "## Market Analysis\n\n*No pricing data available.*"
        
        # Calculate price statistics
        all_prices = {}  # resource_id -> list of prices
        
        for op_prices in self.prices.values():
            for resource_id, price in op_prices.items():
                if resource_id not in all_prices:
                    all_prices[resource_id] = []
                all_prices[resource_id].append(price)
        
        # Price volatility analysis
        price_stats = {}
        for resource_id, price_list in all_prices.items():
            if len(price_list) > 1:
                prices_float = [float(p) for p in price_list]
                mean_price = sum(prices_float) / len(prices_float)
                min_price = min(prices_float)
                max_price = max(prices_float)
                price_range = max_price - min_price
                
                price_stats[resource_id] = {
                    "mean": mean_price,
                    "min": min_price,
                    "max": max_price,
                    "range": price_range,
                    "volatility": price_range / mean_price if mean_price > 0 else 0,
                    "markets": len(price_list)
                }
        
        section = """## Market Analysis

### Price Volatility by Resource

| Resource | Avg Price | Price Range | Volatility | Markets |
|----------|-----------|-------------|------------|---------|"""
        
        # Sort by volatility (descending)
        sorted_stats = sorted(price_stats.items(), key=lambda x: x[1]["volatility"], reverse=True)
        
        for resource_id, stats in sorted_stats[:15]:
            resource_name = resource_id.replace("-", " ").title()
            volatility_pct = stats["volatility"] * 100
            
            section += f"""
| {resource_name} | {stats['mean']:.2f} | {stats['min']:.2f} - {stats['max']:.2f} | {volatility_pct:.1f}% | {stats['markets']} |"""
        
        # Market efficiency analysis
        section += "\n\n### Market Insights\n\n"
        
        high_volatility = [r for r, s in sorted_stats if s["volatility"] > 0.5]
        if high_volatility:
            section += f"**High Price Volatility**: {', '.join(r.replace('-', ' ').title() for r in high_volatility[:5])} show significant price variations across markets, indicating potential arbitrage opportunities.\n\n"
        
        stable_markets = [r for r, s in sorted_stats if s["volatility"] < 0.1 and s["markets"] > 3]
        if stable_markets:
            section += f"**Stable Markets**: {', '.join(r.replace('-', ' ').title() for r in stable_markets[:5])} demonstrate consistent pricing across multiple markets.\n\n"
        
        return section
    
    def _generate_regional_analysis(self) -> str:
        """Generate regional economic analysis."""
        # Group operators by approximate regions (simplified clustering)
        regions = self._cluster_operators_by_region()
        
        section = """## Regional Analysis

### Economic Regions

"""
        
        for region_name, region_ops in regions.items():
            total_pop = sum(op.population for op in region_ops)
            avg_pop = total_pop // len(region_ops) if region_ops else 0
            
            # Count features
            ports = sum(1 for op in region_ops if op.port)
            capitals = sum(1 for op in region_ops if op.capital)
            markets = sum(1 for op in region_ops if op.plaza)
            
            # Tech level distribution
            tech_counts = {}
            for op in region_ops:
                tech_counts[op.tech] = tech_counts.get(op.tech, 0) + 1
            
            dominant_tech = max(tech_counts.items(), key=lambda x: x[1])[0] if tech_counts else TechLevel.TRIBAL
            
            section += f"""#### {region_name}
- **Settlements**: {len(region_ops)} ({total_pop:,} total population, avg: {avg_pop:,})
- **Infrastructure**: {ports} ports, {capitals} capitals, {markets} markets  
- **Dominant Tech**: {str(dominant_tech).title()}
- **Notable Cities**: {', '.join(op.name for op in sorted(region_ops, key=lambda x: x.population, reverse=True)[:3])}

"""
        
        return section
    
    def _generate_appendices(self) -> str:
        """Generate appendices with detailed data."""
        return """## Appendices

### Methodology
This economic analysis uses a deterministic agent-based model to simulate production, consumption, and trade flows between settlements. Key factors include:

- **Production Capacity**: Based on population, technology level, and resource endowments
- **Demand Modeling**: Per-capita consumption adjusted for culture, infrastructure, and wealth
- **Trade Flows**: Greedy profit-maximization algorithm considering transport costs and distance
- **Price Discovery**: Supply/demand ratios with regional and local market effects

### Limitations
- Simplified cultural and technological assumptions
- Static analysis (no temporal dynamics)
- Limited resource complexity
- Approximated geographic relationships

### Technical Details
- **Coordinate System**: WGS84 (EPSG:4326)
- **Distance Calculation**: Great circle distance (Haversine formula)
- **Optimization**: Greedy algorithm for trade flow allocation

---

*Report generated by Economic Worldbuilding Generator v0.1.0*
*For technical support and methodology details, consult the project documentation.*"""
    
    def _cluster_operators_by_region(self) -> Dict[str, List[Operator]]:
        """Simple regional clustering based on geography and culture."""
        regions = {}
        
        for op in self.operators.values():
            # Simple clustering by culture and geography
            culture_tags = [tag for tag in op.tags if tag.startswith("culture_")]
            primary_culture = culture_tags[0].replace("culture_", "").title() if culture_tags else "Mixed"
            
            # Create region names
            if op.coord[0] > 50:  # Northern regions
                region_name = f"Northern {primary_culture}"
            elif op.coord[0] < -30:  # Southern regions  
                region_name = f"Southern {primary_culture}"
            else:  # Central regions
                region_name = f"Central {primary_culture}"
            
            if region_name not in regions:
                regions[region_name] = []
            regions[region_name].append(op)
        
        # Filter out regions with too few operators
        return {name: ops for name, ops in regions.items() if len(ops) >= 3}


# Export main class
__all__ = ["ReportGenerator"]