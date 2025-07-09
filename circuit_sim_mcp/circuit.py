"""Circuit representation and component definitions."""

import keyword
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, validator


def sanitize_node_name(name: str) -> str:
    """Sanitize node name to avoid Python keywords."""
    if keyword.iskeyword(name):
        return f"n_{name}"
    return name


class Component(BaseModel):
    """Base class for circuit components."""
    
    name: str = Field(description="Component name")
    component_type: str = Field(description="Type of component")
    nodes: List[str] = Field(description="List of node names")
    value: Optional[float] = Field(default=None, description="Component value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    
    class Config:
        extra = "allow"
    
    @validator('nodes')
    def validate_nodes(cls, v):
        """Validate that node names are not Python keywords."""
        for node in v:
            if keyword.iskeyword(node):
                raise ValueError(f"Node name '{node}' is a Python keyword. Use '{sanitize_node_name(node)}' instead.")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary."""
        return {
            "name": self.name,
            "type": self.component_type,
            "nodes": self.nodes,
            "value": self.value,
            "unit": self.unit,
            **{k: v for k, v in self.__dict__.items() if k not in ["name", "component_type", "nodes", "value", "unit"]}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Component":
        """Create component from dictionary."""
        comp_type = data.get("type", data.get("component_type", "unknown"))
        
        # Create specific component types
        if comp_type == "resistor":
            return Resistor(**data)
        elif comp_type == "capacitor":
            return Capacitor(**data)
        elif comp_type == "inductor":
            return Inductor(**data)
        elif comp_type == "voltage_source":
            return VoltageSource(**data)
        elif comp_type == "current_source":
            return CurrentSource(**data)
        elif comp_type == "diode":
            return Diode(**data)
        elif comp_type == "transistor":
            return Transistor(**data)
        else:
            return cls(**data)


class Resistor(Component):
    """Resistor component."""
    
    component_type: str = "resistor"
    resistance: float = Field(description="Resistance in ohms")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.value is None:
            self.value = self.resistance
        if self.unit is None:
            self.unit = "Ω"


class Capacitor(Component):
    """Capacitor component."""
    
    component_type: str = "capacitor"
    capacitance: float = Field(description="Capacitance in farads")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.value is None:
            self.value = self.capacitance
        if self.unit is None:
            self.unit = "F"


class Inductor(Component):
    """Inductor component."""
    
    component_type: str = "inductor"
    inductance: float = Field(description="Inductance in henries")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.value is None:
            self.value = self.inductance
        if self.unit is None:
            self.unit = "H"


class VoltageSource(Component):
    """Voltage source component."""
    
    component_type: str = "voltage_source"
    voltage: float = Field(description="Voltage in volts")
    source_type: str = Field(default="DC", description="Source type (DC, AC, pulse, etc.)")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.value is None:
            self.value = self.voltage
        if self.unit is None:
            self.unit = "V"


class CurrentSource(Component):
    """Current source component."""
    
    component_type: str = "current_source"
    current: float = Field(description="Current in amperes")
    source_type: str = Field(default="DC", description="Source type (DC, AC, pulse, etc.)")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.value is None:
            self.value = self.current
        if self.unit is None:
            self.unit = "A"


class Diode(Component):
    """Diode component."""
    
    component_type: str = "diode"
    model: Optional[str] = Field(default=None, description="Diode model name")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.unit is None:
            self.unit = "diode"


class Transistor(Component):
    """Transistor component."""
    
    component_type: str = "transistor"
    transistor_type: str = Field(description="Transistor type (npn, pnp, nmos, pmos)")
    model: Optional[str] = Field(default=None, description="Transistor model name")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.unit is None:
            self.unit = self.transistor_type


class Circuit:
    """Represents an electronic circuit."""
    
    def __init__(self, name: str):
        """Initialize a new circuit."""
        self.name = name
        self.components: List[Component] = []
        self._nodes: Set[str] = set()
    
    def add_component(self, component: Component) -> None:
        """Add a component to the circuit."""
        self.components.append(component)
        self._nodes.update(component.nodes)
    
    def get_nodes(self) -> Set[str]:
        """Get all nodes in the circuit."""
        return self._nodes.copy()
    
    def get_components_by_type(self, component_type: str) -> List[Component]:
        """Get all components of a specific type."""
        return [comp for comp in self.components if comp.component_type == component_type]
    
    def generate_netlist(self) -> str:
        """Generate SPICE netlist for the circuit."""
        netlist_lines = [f"* Circuit: {self.name}"]
        netlist_lines.append("* Generated by Circuit Sim MCP")
        netlist_lines.append("")
        
        for component in self.components:
            netlist_lines.append(self._component_to_netlist(component))
        
        netlist_lines.append("")
        netlist_lines.append(".END")
        
        return "\n".join(netlist_lines)
    
    def _component_to_netlist(self, component: Component) -> str:
        """Convert a component to SPICE netlist format."""
        if component.component_type == "resistor":
            return f"R{component.name} {' '.join(component.nodes)} {component.value}"
        elif component.component_type == "capacitor":
            return f"C{component.name} {' '.join(component.nodes)} {component.value}"
        elif component.component_type == "inductor":
            return f"L{component.name} {' '.join(component.nodes)} {component.value}"
        elif component.component_type == "voltage_source":
            return f"V{component.name} {' '.join(component.nodes)} {component.value}"
        elif component.component_type == "current_source":
            return f"I{component.name} {' '.join(component.nodes)} {component.value}"
        elif component.component_type == "diode":
            model = f" {component.model}" if component.model else ""
            return f"D{component.name} {' '.join(component.nodes)}{model}"
        elif component.component_type == "transistor":
            model = f" {component.model}" if component.model else ""
            return f"Q{component.name} {' '.join(component.nodes)}{model}"
        else:
            return f"* Unknown component: {component.name}"


class SimulationResults(BaseModel):
    """Results from circuit simulation."""
    
    analysis_type: str = Field(description="Type of analysis performed")
    circuit_name: str = Field(description="Name of the circuit")
    data: Dict[str, Any] = Field(description="Simulation data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "analysis_type": self.analysis_type,
            "circuit_name": self.circuit_name,
            "data": self.data,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationResults":
        """Create results from dictionary."""
        return cls(**data) 