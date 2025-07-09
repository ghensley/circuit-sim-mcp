"""Unit tests for the circuit module."""

import pytest
from circuit_sim_mcp.circuit import (
    Circuit, Component, Resistor, Capacitor, Inductor,
    VoltageSource, CurrentSource, Diode, Transistor
)


class TestComponent:
    """Test component creation and functionality."""
    
    def test_resistor_creation(self):
        """Test resistor component creation."""
        resistor = Resistor(
            name="R1",
            nodes=["n1", "n2"],
            resistance=1000.0
        )
        
        assert resistor.name == "R1"
        assert resistor.component_type == "resistor"
        assert resistor.nodes == ["n1", "n2"]
        assert resistor.value == 1000.0
        assert resistor.unit == "Ω"
    
    def test_capacitor_creation(self):
        """Test capacitor component creation."""
        capacitor = Capacitor(
            name="C1",
            nodes=["n1", "n2"],
            capacitance=1e-6
        )
        
        assert capacitor.name == "C1"
        assert capacitor.component_type == "capacitor"
        assert capacitor.nodes == ["n1", "n2"]
        assert capacitor.value == 1e-6
        assert capacitor.unit == "F"
    
    def test_voltage_source_creation(self):
        """Test voltage source component creation."""
        source = VoltageSource(
            name="V1",
            nodes=["n1", "n2"],
            voltage=5.0,
            source_type="DC"
        )
        
        assert source.name == "V1"
        assert source.component_type == "voltage_source"
        assert source.nodes == ["n1", "n2"]
        assert source.value == 5.0
        assert source.unit == "V"
        assert source.source_type == "DC"
    
    def test_component_from_dict(self):
        """Test component creation from dictionary."""
        data = {
            "type": "resistor",
            "name": "R1",
            "nodes": ["n1", "n2"],
            "resistance": 1000.0
        }
        
        component = Component.from_dict(data)
        assert isinstance(component, Resistor)
        assert component.name == "R1"
        assert component.value == 1000.0
    
    def test_component_to_dict(self):
        """Test component conversion to dictionary."""
        resistor = Resistor(
            name="R1",
            nodes=["n1", "n2"],
            resistance=1000.0
        )
        
        data = resistor.to_dict()
        assert data["name"] == "R1"
        assert data["type"] == "resistor"
        assert data["nodes"] == ["n1", "n2"]
        assert data["value"] == 1000.0
        assert data["unit"] == "Ω"


class TestCircuit:
    """Test circuit functionality."""
    
    def test_circuit_creation(self):
        """Test circuit creation."""
        circuit = Circuit("test_circuit")
        
        assert circuit.name == "test_circuit"
        assert len(circuit.components) == 0
        assert len(circuit.get_nodes()) == 0
    
    def test_add_component(self):
        """Test adding components to circuit."""
        circuit = Circuit("test_circuit")
        
        resistor = Resistor(
            name="R1",
            nodes=["n1", "n2"],
            resistance=1000.0
        )
        
        circuit.add_component(resistor)
        
        assert len(circuit.components) == 1
        assert "n1" in circuit.get_nodes()
        assert "n2" in circuit.get_nodes()
    
    def test_get_components_by_type(self):
        """Test getting components by type."""
        circuit = Circuit("test_circuit")
        
        resistor1 = Resistor(name="R1", nodes=["n1", "n2"], resistance=1000.0)
        resistor2 = Resistor(name="R2", nodes=["n2", "n3"], resistance=2000.0)
        capacitor = Capacitor(name="C1", nodes=["n1", "n3"], capacitance=1e-6)
        
        circuit.add_component(resistor1)
        circuit.add_component(resistor2)
        circuit.add_component(capacitor)
        
        resistors = circuit.get_components_by_type("resistor")
        capacitors = circuit.get_components_by_type("capacitor")
        
        assert len(resistors) == 2
        assert len(capacitors) == 1
        assert all(isinstance(r, Resistor) for r in resistors)
        assert all(isinstance(c, Capacitor) for c in capacitors)
    
    def test_generate_netlist(self):
        """Test netlist generation."""
        circuit = Circuit("test_circuit")
        
        resistor = Resistor(name="R1", nodes=["n1", "n2"], resistance=1000.0)
        voltage_source = VoltageSource(name="V1", nodes=["n1", "0"], voltage=5.0)
        
        circuit.add_component(voltage_source)
        circuit.add_component(resistor)
        
        netlist = circuit.generate_netlist()
        
        assert "* Circuit: test_circuit" in netlist
        assert "V1 n1 0 5.0" in netlist
        assert "R1 n1 n2 1000.0" in netlist
        assert ".END" in netlist


class TestSimulationResults:
    """Test simulation results."""
    
    def test_simulation_results_creation(self):
        """Test simulation results creation."""
        data = {"node1": 5.0, "node2": 2.5}
        metadata = {"analysis_type": "DC", "timestamp": "2024-01-01"}
        
        results = SimulationResults(
            analysis_type="DC",
            circuit_name="test_circuit",
            data=data,
            metadata=metadata
        )
        
        assert results.analysis_type == "DC"
        assert results.circuit_name == "test_circuit"
        assert results.data == data
        assert results.metadata == metadata
    
    def test_simulation_results_to_dict(self):
        """Test simulation results conversion to dictionary."""
        data = {"node1": 5.0, "node2": 2.5}
        metadata = {"analysis_type": "DC", "timestamp": "2024-01-01"}
        
        results = SimulationResults(
            analysis_type="DC",
            circuit_name="test_circuit",
            data=data,
            metadata=metadata
        )
        
        result_dict = results.to_dict()
        
        assert result_dict["analysis_type"] == "DC"
        assert result_dict["circuit_name"] == "test_circuit"
        assert result_dict["data"] == data
        assert result_dict["metadata"] == metadata


if __name__ == "__main__":
    pytest.main([__file__]) 