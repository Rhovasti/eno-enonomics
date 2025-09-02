"""Core Pydantic models for the economic worldbuilding generator."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Dict, List, Tuple, Optional, Literal
from decimal import Decimal
from uuid import UUID, uuid4
from enum import Enum


class TechLevel(str, Enum):
    """Technology levels in ascending order."""
    TRIBAL = "tribal"
    MEDIEVAL = "medieval"
    INDUSTRIAL = "industrial"
    
    def __ge__(self, other):
        """Enable comparison: tribal < medieval < industrial."""
        if not isinstance(other, TechLevel):
            return NotImplemented
        order = {self.TRIBAL: 0, self.MEDIEVAL: 1, self.INDUSTRIAL: 2}
        return order[self] >= order[other]
    
    def __gt__(self, other):
        """Enable comparison: tribal < medieval < industrial."""
        if not isinstance(other, TechLevel):
            return NotImplemented
        order = {self.TRIBAL: 0, self.MEDIEVAL: 1, self.INDUSTRIAL: 2}
        return order[self] > order[other]
    
    def __le__(self, other):
        """Enable comparison: tribal < medieval < industrial."""
        if not isinstance(other, TechLevel):
            return NotImplemented
        return not self > other
    
    def __lt__(self, other):
        """Enable comparison: tribal < medieval < industrial."""
        if not isinstance(other, TechLevel):
            return NotImplemented
        return not self >= other


class Resource(BaseModel):
    """Resource definition with tech requirements."""
    model_config = ConfigDict(use_enum_values=True)
    
    resource_id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    name: str
    tier: int = Field(..., ge=0, le=3)  # 0=raw, 1=refined, 2=advanced
    tech_min: TechLevel
    base_price: Decimal = Field(..., gt=0)
    transportable: bool = True
    perishable: bool = False
    
    @field_validator("resource_id")
    @classmethod
    def validate_id(cls, v):
        """Validate resource ID format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Resource ID must be alphanumeric with hyphens")
        return v.lower()


class ProductionRule(BaseModel):
    """Production transformation rules."""
    model_config = ConfigDict(use_enum_values=True)
    
    rule_id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    name: str
    inputs: Dict[str, Decimal]  # resource_id -> quantity
    outputs: Dict[str, Decimal]
    tech_min: TechLevel
    byproducts: Dict[str, Decimal] = Field(default_factory=dict)
    capacity_driver: Optional[str] = None  # endowment that scales capacity
    labor_required: Decimal = Field(default=Decimal("1.0"))
    
    @field_validator("outputs")
    @classmethod
    def validate_outputs(cls, v):
        """Validate output quantities."""
        if not v:
            raise ValueError("Must have at least one output")
        for qty in v.values():
            if qty <= 0:
                raise ValueError("Quantities must be positive")
        return v
    
    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, v):
        """Validate input quantities."""
        # Inputs can be empty for resource extraction rules
        for qty in v.values():
            if qty <= 0:
                raise ValueError("Quantities must be positive")
        return v


class Operator(BaseModel):
    """Economic operator (city, org, building, etc)."""
    model_config = ConfigDict(use_enum_values=True)
    
    operator_id: str
    name: str
    kind: Literal["city", "organization", "building", "district", "person"]
    tech: TechLevel
    coord: Tuple[float, float]  # (lat, lon) in WGS84
    population: int = 0
    tags: List[str] = Field(default_factory=list)
    endowments: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Derived fields
    capital: bool = False
    port: bool = False
    citadel: bool = False
    walls: bool = False
    plaza: bool = False
    temple: bool = False
    shanty_town: bool = False
    
    @field_validator("coord")
    @classmethod
    def validate_coordinates(cls, v):
        """Validate coordinate ranges."""
        lat, lon = v
        if not (-90 <= lat <= 90):
            raise ValueError(f"Invalid latitude: {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Invalid longitude: {lon}")
        return v


class Capacity(BaseModel):
    """Production capacity for operator-rule pair."""
    operator_id: str
    rule_id: str
    max_rate: Decimal = Field(..., gt=0)  # units per time step
    efficiency: Decimal = Field(default=Decimal("1.0"), ge=0, le=2)


class DemandProfile(BaseModel):
    """Per-capita consumption by tech level."""
    model_config = ConfigDict(use_enum_values=True)
    
    tech: TechLevel
    per_capita: Dict[str, Decimal]  # resource_id -> quantity


class TradeLink(BaseModel):
    """Trade flow between operators."""
    link_id: UUID = Field(default_factory=uuid4)
    source_id: str
    dest_id: str
    resource_id: str
    quantity: Decimal = Field(..., gt=0)
    distance_km: Decimal = Field(..., gt=0)
    transport_cost: Decimal = Field(..., ge=0)
    price_source: Decimal
    price_dest: Decimal
    profit_margin: Decimal
    
    @property
    def is_profitable(self) -> bool:
        """Check if trade link is profitable."""
        return self.price_dest > self.price_source + self.transport_cost


class SimulationConfig(BaseModel):
    """Main simulation configuration."""
    model_config = ConfigDict(use_enum_values=True)
    
    # Trade parameters
    max_trade_neighbors: int = Field(default=8, ge=1, le=50)
    max_trade_radius_km: Decimal = Field(default=Decimal("800"), gt=0)
    min_trade_quantity: Decimal = Field(default=Decimal("0.5"), gt=0)
    transport_cost_per_km: Decimal = Field(default=Decimal("0.02"), ge=0)
    
    # Pricing parameters
    scarcity_multiplier: bool = True
    price_elasticity: Decimal = Field(default=Decimal("1.5"), gt=0)
    
    # Simulation parameters
    time_steps: int = Field(default=1, ge=1)
    seed: Optional[int] = None
    strict_validation: bool = True
    parallel_workers: int = Field(default=1, ge=-1)  # -1 for all CPUs


# Export all models
__all__ = [
    "TechLevel",
    "Resource",
    "ProductionRule",
    "Operator",
    "Capacity",
    "DemandProfile",
    "TradeLink",
    "SimulationConfig",
]