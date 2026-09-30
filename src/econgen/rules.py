"""Production rules engine for economic simulation."""

import networkx as nx
from typing import List, Dict, Set
from decimal import Decimal
from .models import ProductionRule, Operator, TechLevel, Capacity
import logging

logger = logging.getLogger(__name__)


class RulesEngine:
    """Manage production rules and capacity calculations."""
    
    def __init__(self, rules: List[ProductionRule]):
        """Initialize rules engine.
        
        Args:
            rules: List of production rules
            
        Raises:
            ValueError: If rules contain circular dependencies
        """
        self.rules = {r.rule_id: r for r in rules}
        self._validate_dag()
        self._validate_resources()
        logger.info(f"Initialized rules engine with {len(self.rules)} rules")
    
    def _validate_dag(self) -> None:
        """Ensure no circular dependencies in production chains.
        
        Raises:
            ValueError: If circular dependencies are detected
        """
        G = nx.DiGraph()
        
        # Build dependency graph: input -> output
        for rule in self.rules.values():
            for output_resource in rule.outputs:
                for input_resource in rule.inputs:
                    G.add_edge(input_resource, output_resource, rule_id=rule.rule_id)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            raise ValueError(f"Circular production dependencies detected: {cycles}")
        
        logger.info(f"Production DAG validated: {len(G.nodes)} resources, {len(G.edges)} dependencies")
    
    def _validate_resources(self) -> None:
        """Log summary of resources referenced in rules."""
        all_resources: Set[str] = set()
        
        for rule in self.rules.values():
            all_resources.update(rule.inputs.keys())
            all_resources.update(rule.outputs.keys())
            all_resources.update(rule.byproducts.keys())
        
        logger.info(f"Found {len(all_resources)} unique resources across all production rules")
    
    def get_rule(self, rule_id: str) -> ProductionRule:
        """Get production rule by ID.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            ProductionRule instance
            
        Raises:
            KeyError: If rule not found
        """
        if rule_id not in self.rules:
            raise KeyError(f"Production rule '{rule_id}' not found")
        return self.rules[rule_id]
    
    def get_eligible_rules(self, operator: Operator) -> List[ProductionRule]:
        """Get production rules available to operator based on tech level and endowments.
        
        Args:
            operator: Economic operator
            
        Returns:
            List of eligible production rules
        """
        eligible = []
        
        for rule in self.rules.values():
            # Check technology requirement
            # Reason: models store tech as plain str (use_enum_values), so compare as enums
            if TechLevel(operator.tech) < TechLevel(rule.tech_min):
                continue
                
            # Check endowment requirement
            if rule.capacity_driver:
                if rule.capacity_driver not in operator.endowments:
                    continue
                if operator.endowments[rule.capacity_driver] <= 0:
                    continue
            
            eligible.append(rule)
        
        logger.debug(f"Operator {operator.operator_id} eligible for {len(eligible)} rules")
        return eligible
    
    def calculate_capacity(self, operator: Operator, rule: ProductionRule) -> Capacity:
        """Calculate production capacity for operator-rule pair.
        
        Args:
            operator: Economic operator
            rule: Production rule
            
        Returns:
            Capacity instance with calculated max_rate and efficiency
        """
        base_capacity = Decimal("1.0")
        efficiency = Decimal("1.0")
        
        # Scale by endowment if specified
        if rule.capacity_driver and rule.capacity_driver in operator.endowments:
            endowment_factor = operator.endowments[rule.capacity_driver]
            # Endowment gives 1-3x multiplier (0=1x, 1=3x, with diminishing returns)
            base_capacity *= (Decimal("1.0") + endowment_factor * Decimal("2.0"))
        
        # Scale by population (labor availability)
        if operator.population > 0:
            # Base labor factor: population per 10k gives multiplier
            labor_factor = Decimal(str(operator.population)) / Decimal("10000")
            # Apply diminishing returns
            labor_factor = labor_factor.sqrt()
            # Cap at reasonable maximum
            labor_factor = min(labor_factor, Decimal("5.0"))
            base_capacity *= max(Decimal("0.1"), labor_factor)
        
        # Technology level bonus
        tech_multipliers = {
            TechLevel.TRIBAL: Decimal("0.5"),
            TechLevel.MEDIEVAL: Decimal("1.0"),
            TechLevel.INDUSTRIAL: Decimal("2.0"),
        }
        base_capacity *= tech_multipliers[operator.tech]
        
        # Infrastructure bonuses
        if operator.plaza and "market" in [t for t in operator.tags if "market" in t.lower()]:
            base_capacity *= Decimal("1.2")  # Market bonus
            
        if operator.port and rule.rule_id in ["fishing", "trade-goods", "import-export"]:
            base_capacity *= Decimal("1.5")  # Port bonus for relevant activities
            
        # Apply labor requirement scaling
        if rule.labor_required > 0:
            labor_adjustment = Decimal("1.0") / rule.labor_required.sqrt()
            base_capacity *= labor_adjustment
        
        # Calculate efficiency based on operator attributes
        if operator.capital:
            efficiency *= Decimal("1.1")  # Capital city efficiency bonus
            
        # Clamp to reasonable bounds
        base_capacity = max(Decimal("0.01"), min(base_capacity, Decimal("1000")))
        efficiency = max(Decimal("0.1"), min(efficiency, Decimal("2.0")))
        
        return Capacity(
            operator_id=operator.operator_id,
            rule_id=rule.rule_id,
            max_rate=base_capacity,
            efficiency=efficiency
        )
    
    def get_production_chain(self, target_resource: str) -> List[ProductionRule]:
        """Get ordered production chain to produce target resource.
        
        Args:
            target_resource: Resource to produce
            
        Returns:
            List of rules in dependency order (inputs before outputs)
        """
        # Find all rules that produce the target resource
        target_rules = [rule for rule in self.rules.values() 
                       if target_resource in rule.outputs]
        
        if not target_rules:
            return []
        
        # Build dependency graph for chain analysis
        G = nx.DiGraph()
        for rule in self.rules.values():
            G.add_node(rule.rule_id)
            for output_resource in rule.outputs:
                for other_rule in self.rules.values():
                    if rule.rule_id != other_rule.rule_id:
                        if output_resource in other_rule.inputs:
                            G.add_edge(rule.rule_id, other_rule.rule_id)
        
        # Get topological ordering for the most productive target rule
        main_rule = max(target_rules, key=lambda r: sum(r.outputs.values()))
        
        try:
            ancestors = nx.ancestors(G, main_rule.rule_id)
            subgraph = G.subgraph(ancestors | {main_rule.rule_id})
            ordered_ids = list(nx.topological_sort(subgraph))
            return [self.rules[rule_id] for rule_id in ordered_ids]
        except nx.NetworkXError:
            # If graph has issues, just return the target rule
            return [main_rule]
    
    def get_rules_by_tech(self, tech_level: TechLevel) -> List[ProductionRule]:
        """Get all rules available at specified technology level.
        
        Args:
            tech_level: Technology level
            
        Returns:
            List of available production rules
        """
        return [rule for rule in self.rules.values() if TechLevel(rule.tech_min) <= TechLevel(tech_level)]
    
    def get_rules_summary(self) -> Dict[str, any]:
        """Get summary statistics about production rules.
        
        Returns:
            Dictionary with rule statistics
        """
        total_rules = len(self.rules)
        by_tech = {str(level): len(self.get_rules_by_tech(level)) for level in TechLevel}
        
        total_inputs = sum(len(rule.inputs) for rule in self.rules.values())
        total_outputs = sum(len(rule.outputs) for rule in self.rules.values())
        
        capacity_driven = sum(1 for rule in self.rules.values() if rule.capacity_driver)
        
        return {
            "total_rules": total_rules,
            "by_tech_level": by_tech,
            "total_inputs": total_inputs,
            "total_outputs": total_outputs,
            "capacity_driven_rules": capacity_driven,
            "avg_inputs_per_rule": total_inputs / total_rules if total_rules > 0 else 0,
            "avg_outputs_per_rule": total_outputs / total_rules if total_rules > 0 else 0,
        }


def create_default_rules() -> List[ProductionRule]:
    """Create default production rules for testing and examples.
    
    Returns:
        List of basic ProductionRule instances
    """
    return [
        # Basic food production
        ProductionRule(
            rule_id="farming",
            name="Farming",
            tech_min=TechLevel.TRIBAL,
            inputs={"seed": Decimal("1.0")},
            outputs={"food": Decimal("3.0")},
            capacity_driver="agriculture",
            labor_required=Decimal("2.0")
        ),
        
        # Fishing
        ProductionRule(
            rule_id="fishing",
            name="Fishing",
            tech_min=TechLevel.TRIBAL,
            inputs={},
            outputs={"fish": Decimal("2.0")},
            capacity_driver="fishing",
            labor_required=Decimal("1.5")
        ),
        
        # Raw material extraction
        ProductionRule(
            rule_id="seed-cultivation",
            name="Seed Cultivation",
            tech_min=TechLevel.TRIBAL,
            inputs={},
            outputs={"seed": Decimal("4.0")},
            capacity_driver="agriculture",
            labor_required=Decimal("1.0")
        ),
        ProductionRule(
            rule_id="fiber-farming",
            name="Fiber Farming",
            tech_min=TechLevel.TRIBAL,
            inputs={},
            outputs={"fiber": Decimal("2.0")},
            capacity_driver="agriculture",
            labor_required=Decimal("2.0")
        ),
        ProductionRule(
            rule_id="precious-metal-mining",
            name="Precious Metal Mining",
            tech_min=TechLevel.MEDIEVAL,
            inputs={},
            outputs={"precious-metals": Decimal("0.5")},
            capacity_driver="mining_potential",
            labor_required=Decimal("5.0")
        ),
        ProductionRule(
            rule_id="gem-mining",
            name="Gem Mining",
            tech_min=TechLevel.MEDIEVAL,
            inputs={},
            outputs={"gems": Decimal("0.3")},
            capacity_driver="mining_potential",
            labor_required=Decimal("5.0")
        ),
        ProductionRule(
            rule_id="forestry",
            name="Forestry",
            tech_min=TechLevel.TRIBAL,
            inputs={},
            outputs={"wood": Decimal("2.5")},
            capacity_driver="forestry",
            labor_required=Decimal("2.0")
        ),
        ProductionRule(
            rule_id="quarrying",
            name="Stone Quarrying",
            tech_min=TechLevel.TRIBAL,
            inputs={},
            outputs={"stone": Decimal("2.0")},
            capacity_driver="mining_potential",
            labor_required=Decimal("3.0")
        ),
        ProductionRule(
            rule_id="iron-mining",
            name="Iron Mining",
            tech_min=TechLevel.MEDIEVAL,
            inputs={},
            outputs={"iron-ore": Decimal("1.5")},
            capacity_driver="mining_potential",
            labor_required=Decimal("4.0")
        ),
        ProductionRule(
            rule_id="coal-mining",
            name="Coal Mining",
            tech_min=TechLevel.MEDIEVAL,
            inputs={},
            outputs={"coal": Decimal("1.8")},
            capacity_driver="mining_potential",
            labor_required=Decimal("4.5")
        ),
        
        # Tool making
        ProductionRule(
            rule_id="toolmaking",
            name="Tool Making",
            tech_min=TechLevel.TRIBAL,
            inputs={"wood": Decimal("2.0"), "stone": Decimal("1.0")},
            outputs={"tools": Decimal("1.0")},
            capacity_driver="craftsmanship",
            labor_required=Decimal("3.0")
        ),
        
        # Textile production
        ProductionRule(
            rule_id="weaving",
            name="Weaving",
            tech_min=TechLevel.MEDIEVAL,
            inputs={"fiber": Decimal("2.0")},
            outputs={"textiles": Decimal("1.5")},
            capacity_driver="general_labor",
            labor_required=Decimal("2.5")
        ),
        
        # Steel production
        ProductionRule(
            rule_id="steel-making",
            name="Steel Making",
            tech_min=TechLevel.INDUSTRIAL,
            inputs={"iron-ore": Decimal("4.0"), "coal": Decimal("2.0")},
            outputs={"steel": Decimal("1.0")},
            byproducts={"slag": Decimal("0.5")},
            capacity_driver="industrial_capacity",
            labor_required=Decimal("5.0")
        ),
        
        # Advanced machinery
        ProductionRule(
            rule_id="machinery-production",
            name="Machinery Production",
            tech_min=TechLevel.INDUSTRIAL,
            inputs={"steel": Decimal("3.0"), "tools": Decimal("1.0")},
            outputs={"machinery": Decimal("1.0")},
            capacity_driver="skilled_labor",
            labor_required=Decimal("8.0")
        ),
        
        # Luxury jewelry
        ProductionRule(
            rule_id="jewelry-crafting",
            name="Jewelry Crafting",
            tech_min=TechLevel.MEDIEVAL,
            inputs={"precious-metals": Decimal("1.0"), "gems": Decimal("0.5")},
            outputs={"jewelry": Decimal("1.0")},
            capacity_driver="craftsmanship",
            labor_required=Decimal("6.0")
        ),
    ]


# Export main classes and functions
__all__ = ["RulesEngine", "create_default_rules"]