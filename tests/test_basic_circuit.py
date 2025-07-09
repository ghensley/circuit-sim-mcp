"""Test basic circuit functionality."""

import pytest
from circuit_sim_mcp.circuit import Component, Circuit


class TestBasicCircuit:
    """Test basic circuit operations."""
    
    def test_component_creation(self):
        """Test creating basic components."""
        # Test resistor
        resistor = Component(
            name="R1",
            component_type="resistor", 
            nodes=["n1", "n2"],
            value=1000.0
        )
        assert resistor.name == "R1"
        assert resistor.component_type == "resistor"
        assert resistor.nodes == ["n1", "n2"]
        assert resistor.value == 1000.0
    
    def test_circuit_creation(self):
        """Test creating and managing circuits."""
        circuit = Circuit("test_circuit")
        assert circuit.name == "test_circuit"
        assert len(circuit.components) == 0
        assert len(circuit.get_nodes()) == 0
    
    def test_adding_components(self):
        """Test adding components to a circuit."""
        circuit = Circuit("voltage_divider")
        
        # Add voltage source
        v1 = Component(
            name="V1",
            component_type="voltage_source",
            nodes=["vin", "gnd"],
            value=10.0
        )
        circuit.add_component(v1)
        
        # Add resistors
        r1 = Component(
            name="R1", 
            component_type="resistor",
            nodes=["vin", "vout"],
            value=1000.0
        )
        circuit.add_component(r1)
        
        r2 = Component(
            name="R2",
            component_type="resistor", 
            nodes=["vout", "gnd"],
            value=1000.0
        )
        circuit.add_component(r2)
        
        # Check circuit state
        assert len(circuit.components) == 3
        assert len(circuit.get_nodes()) == 3  # vin, vout, gnd
        assert "vin" in circuit.get_nodes()
        assert "vout" in circuit.get_nodes()
        assert "gnd" in circuit.get_nodes()
    
    def test_component_from_dict(self):
        """Test creating components from dictionary."""
        comp_data = {
            "name": "R1",
            "type": "resistor", 
            "nodes": ["n1", "n2"],
            "value": 1000.0
        }
        
        component = Component.from_dict(comp_data)
        assert component.name == "R1"
        assert component.component_type == "resistor"
        assert component.nodes == ["n1", "n2"]
        assert component.value == 1000.0
    
    def test_component_to_dict(self):
        """Test converting components to dictionary."""
        component = Component(
            name="C1",
            component_type="capacitor",
            nodes=["n1", "n2"], 
            value=1e-6
        )
        
        comp_dict = component.to_dict()
        assert comp_dict["name"] == "C1"
        assert comp_dict["type"] == "capacitor"
        assert comp_dict["nodes"] == ["n1", "n2"]
        assert comp_dict["value"] == 1e-6
    
    def test_netlist_generation(self):
        """Test generating SPICE netlist."""
        circuit = Circuit("simple_circuit")
        
        # Add a simple resistor circuit
        v1 = Component(
            name="V1",
            component_type="voltage_source",
            nodes=["vin", "gnd"],
            value=5.0
        )
        circuit.add_component(v1)
        
        r1 = Component(
            name="R1",
            component_type="resistor",
            nodes=["vin", "gnd"],
            value=1000.0
        )
        circuit.add_component(r1)
        
        netlist = circuit.generate_netlist()
        
        # Check netlist contains expected elements
        assert "Circuit: simple_circuit" in netlist
        assert "V1" in netlist
        assert "R1" in netlist
        assert ".END" in netlist
    
    def test_node_validation(self):
        """Test that Python keywords are rejected as node names."""
        with pytest.raises(ValueError):
            Component(
                name="BAD",
                component_type="resistor",
                nodes=["in", "out"],  # 'in' is a Python keyword
                value=1000.0
            )
    
    def test_get_components_by_type(self):
        """Test filtering components by type."""
        circuit = Circuit("mixed_circuit")
        
        # Add different component types
        circuit.add_component(Component(
            name="R1", component_type="resistor", 
            nodes=["n1", "n2"], value=1000.0
        ))
        circuit.add_component(Component(
            name="R2", component_type="resistor",
            nodes=["n2", "n3"], value=2000.0
        ))
        circuit.add_component(Component(
            name="C1", component_type="capacitor",
            nodes=["n1", "gnd"], value=1e-6
        ))
        
        resistors = circuit.get_components_by_type("resistor")
        capacitors = circuit.get_components_by_type("capacitor")
        
        assert len(resistors) == 2
        assert len(capacitors) == 1
        assert resistors[0].name in ["R1", "R2"]
        assert capacitors[0].name == "C1"


if __name__ == "__main__":
    pytest.main([__file__]) 