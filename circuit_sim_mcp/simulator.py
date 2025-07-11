"""Circuit simulator using PySpice."""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from PySpice.Spice.Netlist import Circuit as PySpiceCircuit
    from PySpice.Spice.Netlist import Netlist
    from PySpice.Unit import *
    PYSPICE_AVAILABLE = True
except ImportError:
    PYSPICE_AVAILABLE = False

from .circuit import Circuit, SimulationResults


class CircuitSimulationError(Exception):
    """Custom exception for circuit simulation errors."""
    def __init__(self, message: str, suggestion: str = None, technical_details: str = None):
        self.message = message
        self.suggestion = suggestion
        self.technical_details = technical_details
        super().__init__(self.message)
    
    def __str__(self):
        """Return a comprehensive error message including suggestions and technical details."""
        result = [self.message]
        
        if self.suggestion:
            result.append(f"\nSuggestion: {self.suggestion}")
        
        # For debugging, include technical details in the main error output
        if self.technical_details:
            result.append(f"\nTechnical Details:\n{self.technical_details}")
        
        return "".join(result)
    
    def to_dict(self):
        """Return error information as a dictionary for API responses."""
        return {
            "error": self.message,
            "suggestion": self.suggestion,
            "technical_details": self.technical_details
        }


class CircuitSimulator:
    """Circuit simulator using PySpice."""
    
    def __init__(self):
        """Initialize the simulator."""
        self._last_results: Optional[SimulationResults] = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        if not PYSPICE_AVAILABLE:
            raise CircuitSimulationError(
                "PySpice is not available",
                "Install PySpice: pip install PySpice",
                "PySpice requires ngspice to be installed on your system"
            )
    
    def simulate_dc(
        self, 
        circuit: Circuit, 
        output_nodes: Optional[List[str]] = None
    ) -> SimulationResults:
        """Perform DC analysis on a circuit."""
        try:
            # Create PySpice circuit
            spice_circuit = self._create_spice_circuit(circuit)
            
            # Perform DC operating point analysis
            simulator = spice_circuit.simulator(temperature=25, nominal_temperature=25)
            analysis = simulator.operating_point()
            
            # Process results
            data = self._process_dc_results(analysis, output_nodes or list(circuit.get_nodes()))
            
            self._last_results = SimulationResults(
                analysis_type="DC",
                circuit_name=circuit.name,
                data=data,
                metadata={
                    "output_nodes": output_nodes,
                    "total_nodes": len(circuit.get_nodes())
                }
            )
            
            return self._last_results
            
        except Exception as e:
            self._raise_simulation_error("DC", e, circuit)
    
    def simulate_ac(
        self, 
        circuit: Circuit, 
        start_freq: float, 
        stop_freq: float, 
        num_points: int = 100,
        output_nodes: Optional[List[str]] = None
    ) -> SimulationResults:
        """Perform AC analysis on a circuit."""
        try:
            # Create PySpice circuit
            spice_circuit = self._create_spice_circuit(circuit)
            
            # Perform AC analysis
            simulator = spice_circuit.simulator(temperature=25, nominal_temperature=25)
            analysis = simulator.ac(
                start_frequency=start_freq@u_Hz,
                stop_frequency=stop_freq@u_Hz,
                number_of_points=num_points,
                variation='dec'
            )
            
            # Process results
            data = self._process_ac_results(analysis, output_nodes or list(circuit.get_nodes()))
            
            self._last_results = SimulationResults(
                analysis_type="AC",
                circuit_name=circuit.name,
                data=data,
                metadata={
                    "start_frequency": start_freq,
                    "stop_frequency": stop_freq,
                    "num_points": num_points,
                    "output_nodes": output_nodes
                }
            )
            
            return self._last_results
            
        except Exception as e:
            self._raise_simulation_error("AC", e, circuit)
    
    def simulate_transient(
        self, 
        circuit: Circuit, 
        duration: float, 
        step_size: float,
        output_nodes: Optional[List[str]] = None
    ) -> SimulationResults:
        """Perform transient analysis on a circuit."""
        try:
            # Create PySpice circuit
            spice_circuit = self._create_spice_circuit(circuit)
            
            # Perform transient analysis
            simulator = spice_circuit.simulator(temperature=25, nominal_temperature=25)
            analysis = simulator.transient(
                step_time=step_size@u_s,
                end_time=duration@u_s
            )
            
            # Process results
            data = self._process_transient_results(analysis, output_nodes or list(circuit.get_nodes()))
            
            self._last_results = SimulationResults(
                analysis_type="Transient",
                circuit_name=circuit.name,
                data=data,
                metadata={
                    "duration": duration,
                    "step_size": step_size,
                    "output_nodes": output_nodes
                }
            )
            
            return self._last_results
            
        except Exception as e:
            self._raise_simulation_error("Transient", e, circuit)
    
    def _create_spice_circuit(self, circuit: Circuit) -> PySpiceCircuit:
        """Create a PySpice circuit from our Circuit object."""
        try:
            spice_circuit = PySpiceCircuit(circuit.name)
            
            # Add default diode model if any diodes are present
            diodes = circuit.get_components_by_type("diode")
            if diodes:
                # Add basic default diode model
                spice_circuit.model('DefaultDiode', 'D', is_=1e-14, rs=10, cjo=1e-12)
            
            for component in circuit.components:
                self._add_component_to_spice(spice_circuit, component)
            
            return spice_circuit
        except Exception as e:
            raise CircuitSimulationError(
                "Failed to create SPICE circuit from component definitions",
                "Check that all components have valid values and node connections",
                f"Error during circuit creation: {e}"
            )
    
    def _add_component_to_spice(self, spice_circuit: PySpiceCircuit, component: Any) -> None:
        """Add a component to the PySpice circuit."""
        if component.component_type == "resistor":
            spice_circuit.R(component.name, *component.nodes, component.value@u_Ω)
        elif component.component_type == "capacitor":
            spice_circuit.C(component.name, *component.nodes, component.value@u_F)
        elif component.component_type == "inductor":
            spice_circuit.L(component.name, *component.nodes, component.value@u_H)
        elif component.component_type == "voltage_source":
            if component.source_type == "DC":
                spice_circuit.V(component.name, *component.nodes, component.value@u_V)
            elif component.source_type == "AC":
                spice_circuit.V(component.name, *component.nodes, component.value@u_V)
        elif component.component_type == "current_source":
            if component.source_type == "DC":
                spice_circuit.I(component.name, *component.nodes, component.value@u_A)
            elif component.source_type == "AC":
                spice_circuit.I(component.name, *component.nodes, component.value@u_A)
        elif component.component_type == "diode":
            # Use default diode model with explicit model specification
            spice_circuit.D(component.name, component.nodes[0], component.nodes[1], model='DefaultDiode')
        elif component.component_type == "transistor":
            model = component.model if component.model else component.transistor_type
            spice_circuit.Q(component.name, *component.nodes, model)
    
    def _process_dc_results(self, results: Any, output_nodes: List[str]) -> Dict[str, Any]:
        """Process DC operating point analysis results."""
        data = {}
        try:
            # Operating point results are accessed via results.nodes
            for node in output_nodes:
                # Handle ground nodes specially - they're the reference (0V) and not included in results
                if node.lower() in ['gnd', '0', 'ground']:
                    data[node] = 0.0
                elif hasattr(results, 'nodes') and node in results.nodes:
                    data[node] = float(results.nodes[node])
                elif hasattr(results, node):
                    # Fallback for other result formats
                    data[node] = float(getattr(results, node))
                else:
                    # Provide detailed error information
                    available_nodes = []
                    if hasattr(results, 'nodes'):
                        available_nodes = list(results.nodes.keys())
                    else:
                        available_nodes = [attr for attr in dir(results) if not attr.startswith('_')]
                    
                    # Add ground nodes to available list since they're valid
                    available_nodes.extend(['gnd', '0'])
                    
                    raise CircuitSimulationError(
                        f"Node '{node}' not found in simulation results",
                        "Check that the node name exists in your circuit and is connected to components",
                        f"Available nodes: {available_nodes}"
                    )
        except AttributeError as e:
            raise CircuitSimulationError(
                "Failed to extract DC analysis results",
                "The simulation may have failed or returned invalid results",
                f"Result processing error: {e}"
            )
        
        return data
    
    def _process_ac_results(self, results: Any, output_nodes: List[str]) -> Dict[str, Any]:
        """Process AC analysis results."""
        data = {"frequency": []}
        try:
            # Get frequency data
            if hasattr(results, 'frequency'):
                data["frequency"] = [float(f) for f in results.frequency]
            else:
                raise CircuitSimulationError(
                    "No frequency data found in AC analysis results",
                    "The AC simulation may have failed or returned invalid results"
                )
            
            # Get node data
            for node in output_nodes:
                if hasattr(results, node):
                    node_data = getattr(results, node)
                    if hasattr(node_data, 'magnitude'):
                        data[f"{node}_magnitude"] = [float(m) for m in node_data.magnitude]
                    if hasattr(node_data, 'phase'):
                        data[f"{node}_phase"] = [float(p) for p in node_data.phase]
                else:
                    raise CircuitSimulationError(
                        f"Node '{node}' not found in AC analysis results",
                        "Check that the node name exists in your circuit",
                        f"Available nodes: {[attr for attr in dir(results) if not attr.startswith('_')]}"
                    )
        except AttributeError as e:
            raise CircuitSimulationError(
                "Failed to extract AC analysis results",
                "The simulation may have failed or returned invalid results",
                f"Result processing error: {e}"
            )
        
        return data
    
    def _process_transient_results(self, results: Any, output_nodes: List[str]) -> Dict[str, Any]:
        """Process transient analysis results."""
        data = {"time": []}
        try:
            # Get time data
            if hasattr(results, 'time'):
                data["time"] = [float(t) for t in results.time]
            else:
                raise CircuitSimulationError(
                    "No time data found in transient analysis results",
                    "The transient simulation may have failed or returned invalid results"
                )
            
            # Get node data
            for node in output_nodes:
                if hasattr(results, node):
                    node_data = getattr(results, node)
                    data[node] = [float(v) for v in node_data]
                else:
                    raise CircuitSimulationError(
                        f"Node '{node}' not found in transient analysis results",
                        "Check that the node name exists in your circuit",
                        f"Available nodes: {[attr for attr in dir(results) if not attr.startswith('_')]}"
                    )
        except AttributeError as e:
            raise CircuitSimulationError(
                "Failed to extract transient analysis results",
                "The simulation may have failed or returned invalid results",
                f"Result processing error: {e}"
            )
        
        return data
    
    def _raise_simulation_error(self, analysis_type: str, original_error: Exception, circuit: Circuit):
        """Raise a descriptive simulation error with detailed diagnostics."""
        error_str = str(original_error).lower()
        
        # Generate circuit diagnostics
        diagnostics = self._generate_circuit_diagnostics(circuit)
        
        # Detailed SPICE error parsing
        if "ngspice" in error_str or "simulator" in error_str:
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: ngspice not found or not working",
                "Install ngspice: brew install ngspice (macOS) or sudo apt-get install ngspice (Ubuntu)",
                f"Original error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "singular matrix" in error_str or "convergence" in error_str:
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: Singular matrix (no DC solution)",
                "FIXES: 1) Add ground connection to node 'gnd' or '0', 2) Check for floating nodes, 3) Verify all components are properly connected, 4) Add small resistance (1mΩ) in series with voltage sources",
                f"Original error: {original_error}\n\nThis typically means the circuit has no valid DC operating point.\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "model" in error_str and "not found" in error_str:
            # Extract model name if possible
            model_match = None
            import re
            match = re.search(r"model[s]?\s+['\"]?(\w+)['\"]?\s+not found", error_str)
            if match:
                model_match = match.group(1)
            
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: Missing model definition" + (f" '{model_match}'" if model_match else ""),
                f"FIXES: 1) Use built-in models: 'D' or 'LED' for diodes, 2) Remove model field to use defaults, 3) Check spelling of model name",
                f"Available models: D (basic diode), LED (light emitting diode)\n\nOriginal error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "unknown device" in error_str or "unrecognized" in error_str:
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: Unknown component type or model",
                "FIXES: 1) Check component_type field matches: resistor, capacitor, inductor, voltage_source, current_source, diode, transistor, 2) Verify model names for semiconductors",
                f"Original error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "node" in error_str and ("undefined" in error_str or "unknown" in error_str):
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: Undefined node reference",
                "FIXES: 1) Check all node names are consistent across components, 2) Ensure ground node 'gnd' or '0' exists, 3) Check for typos in node names",
                f"Original error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "terminal" in error_str or "pin" in error_str:
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: Component terminal/pin error",
                "FIXES: 1) Check node count matches component type (resistors need 2, transistors need 3), 2) Verify node names don't contain special characters",
                f"Original error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "command" in error_str and "run" in error_str:
            # This is the specific "Command 'run' failed" error - provide more detailed analysis
            netlist = circuit.generate_netlist()
            
            # Extract more details from the original error for transparency
            original_error_type = type(original_error).__name__
            original_error_msg = str(original_error)
            
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: {original_error_type}: {original_error_msg}",
                "COMMON CAUSES: 1) Missing ground connection, 2) Floating nodes, 3) Invalid component models, 4) Malformed netlist. Use debug_simulation tool for detailed SPICE output analysis.",
                f"Generated netlist:\n{netlist}\n\nFull original error details:\n{original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "value" in error_str or "parameter" in error_str:
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: Invalid component parameter",
                "FIXES: 1) Check all component values are positive numbers, 2) Verify units (Ω, F, H, V, A), 3) Avoid extremely large or small values",
                f"Original error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "analysis" in error_str or "directive" in error_str:
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: SPICE analysis directive error",
                "FIXES: 1) This is likely an internal PySpice issue, 2) Try debug_simulation tool, 3) Check if circuit has any unusual components",
                f"Original error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        elif "syntax" in error_str or "parse" in error_str:
            netlist = circuit.generate_netlist()
            raise CircuitSimulationError(
                f"{analysis_type} simulation failed: SPICE netlist syntax error",
                "FIXES: 1) Check for special characters in component names, 2) Verify node names are valid, 3) Check netlist format below",
                f"Generated netlist:\n{netlist}\n\nOriginal error: {original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )
        else:
            # Pass through original error with helpful guidance
            netlist = circuit.generate_netlist()
            
            # Extract the core error message for better transparency
            original_error_type = type(original_error).__name__
            original_error_msg = str(original_error)
            
            # Create a more transparent error message
            transparent_message = f"{analysis_type} simulation failed: {original_error_type}: {original_error_msg}"
            
            raise CircuitSimulationError(
                transparent_message,
                "DEBUGGING STEPS: 1) Use debug_simulation tool for detailed SPICE output, 2) Check the netlist below for syntax issues, 3) Try create_example_circuit to test working examples, 4) Use validate_circuit to identify common problems",
                f"Generated netlist:\n{netlist}\n\nFull original error details:\n{original_error}\n\nCircuit diagnostics:\n{diagnostics}"
            )

    def _generate_circuit_diagnostics(self, circuit: Circuit) -> str:
        """Generate detailed circuit diagnostics for debugging."""
        lines = []
        
        # Basic circuit info
        lines.append(f"Circuit: {circuit.name}")
        lines.append(f"Components: {len(circuit.components)}")
        lines.append(f"Nodes: {len(circuit.get_nodes())}")
        lines.append("")
        
        # Node analysis
        nodes = circuit.get_nodes()
        lines.append("Node Analysis:")
        if "gnd" not in nodes and "0" not in nodes:
            lines.append("  ⚠️  NO GROUND CONNECTION FOUND - Add node 'gnd' or '0'")
        else:
            lines.append("  ✅ Ground connection found")
        
        # Node connection count
        node_connections = {}
        for component in circuit.components:
            for node in component.nodes:
                node_connections[node] = node_connections.get(node, 0) + 1
        
        floating_nodes = [node for node, count in node_connections.items() if count == 1]
        if floating_nodes:
            lines.append(f"  ⚠️  Floating nodes (only 1 connection): {floating_nodes}")
        else:
            lines.append("  ✅ No floating nodes detected")
        lines.append("")
        
        # Component analysis
        lines.append("Component Analysis:")
        component_types = {}
        for component in circuit.components:
            comp_type = component.component_type
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        for comp_type, count in component_types.items():
            lines.append(f"  {comp_type}: {count}")
        
        # Check for voltage sources
        if "voltage_source" not in component_types:
            lines.append("  ⚠️  NO VOLTAGE SOURCES - DC analysis needs at least one voltage source")
        
        # Check for extreme values
        lines.append("")
        lines.append("Value Analysis:")
        extreme_values = []
        for component in circuit.components:
            if hasattr(component, 'value') and component.value:
                if component.component_type == "resistor":
                    if component.value <= 0:
                        extreme_values.append(f"  ⚠️  {component.name}: Invalid resistance {component.value}Ω (must be > 0)")
                    elif component.value < 0.1 or component.value > 1e9:
                        extreme_values.append(f"  ⚠️  {component.name}: Extreme resistance {component.value}Ω (recommended: 0.1Ω to 1GΩ)")
                elif component.component_type == "capacitor":
                    if component.value <= 0:
                        extreme_values.append(f"  ⚠️  {component.name}: Invalid capacitance {component.value}F (must be > 0)")
                    elif component.value < 1e-15 or component.value > 1e-3:
                        extreme_values.append(f"  ⚠️  {component.name}: Extreme capacitance {component.value}F (recommended: 1fF to 1mF)")
        
        if extreme_values:
            lines.extend(extreme_values)
        else:
            lines.append("  ✅ All component values appear reasonable")
        
        lines.append("")
        lines.append("Generated SPICE Netlist:")
        lines.append(circuit.generate_netlist())
        
        return "\n".join(lines) 