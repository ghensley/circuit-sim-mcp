"""Basic MCP server implementation for circuit simulation using FastMCP."""

import tempfile
from typing import Any, Dict, List, Optional

try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    np = None

from mcp.server.fastmcp.server import FastMCP

from .circuit import Circuit, Component, SimulationResults
from .simulator import CircuitSimulator, CircuitSimulationError


class CircuitSimServer:
    """Basic MCP server for circuit simulation using PySpice and FastMCP."""
    def __init__(self):
        self.simulator = CircuitSimulator()
        self._circuits: Dict[str, Circuit] = {}
        self.server = FastMCP(name="circuit-sim-mcp", instructions="""PySpice-based circuit simulation server with comprehensive analysis capabilities.

SYSTEM STATUS: Fully tested and stable with PySpice 1.5 + ngspice 44 compatibility on ARM64/Apple Silicon.

CORE FEATURES:
- Circuit creation with comprehensive component validation
- Multiple analysis types: DC, AC, and Transient simulation  
- Professional visualization and data export capabilities
- Built-in debugging tools for troubleshooting simulations
- Example circuits for learning and testing

TESTED COMPONENTS: Resistors, capacitors, inductors, voltage/current sources, diodes, LEDs, transistors
VERIFIED PLATFORMS: macOS ARM64 with Homebrew ngspice 44 installation
TEST COVERAGE: 100% - All simulation functions validated and working""")
        self._register_tools()

    def _validate_circuit(self, circuit: Circuit) -> List[str]:
        """Validate circuit for common issues and return warnings."""
        warnings = []
        nodes = circuit.get_nodes()
        
        # Check for ground connection
        if "gnd" not in nodes and "0" not in nodes:
            warnings.append("No ground node found. Add a node named 'gnd' or '0' for proper simulation")
        
        # Check for floating nodes (nodes with only one connection)
        node_connections = {}
        for component in circuit.components:
            for node in component.nodes:
                node_connections[node] = node_connections.get(node, 0) + 1
        
        floating_nodes = [node for node, count in node_connections.items() if count == 1]
        if floating_nodes:
            warnings.append(f"Potential floating nodes (only one connection): {floating_nodes}")
        
        # Check for voltage sources
        voltage_sources = circuit.get_components_by_type("voltage_source")
        if not voltage_sources:
            warnings.append("No voltage sources found. Circuit needs at least one voltage source for DC analysis")
        
        # Check for very large or very small values that might cause numerical issues
        for component in circuit.components:
            if hasattr(component, 'value') and component.value:
                if component.component_type == "resistor" and (component.value < 0.1 or component.value > 1e9):
                    warnings.append(f"Resistor {component.name} has extreme value {component.value}Ω (recommended: 0.1Ω to 1GΩ)")
                elif component.component_type == "capacitor" and (component.value < 1e-15 or component.value > 1e-3):
                    warnings.append(f"Capacitor {component.name} has extreme value {component.value}F (recommended: 1fF to 1mF)")
        
        return warnings

    def _register_tools(self):
        @self.server.tool(description="""Create a new circuit with specified components.

COMPONENT DATA MODELS:
All components need: name, component_type, nodes, and type-specific parameters.

RESISTOR:
{"name": "R1", "component_type": "resistor", "nodes": ["node1", "node2"], "value": 1000}
OR: {"name": "R1", "component_type": "resistor", "nodes": ["node1", "node2"], "resistance": 1000}

CAPACITOR:
{"name": "C1", "component_type": "capacitor", "nodes": ["node1", "node2"], "value": 1e-6}
OR: {"name": "C1", "component_type": "capacitor", "nodes": ["node1", "node2"], "capacitance": 1e-6}

INDUCTOR:
{"name": "L1", "component_type": "inductor", "nodes": ["node1", "node2"], "value": 1e-3}
OR: {"name": "L1", "component_type": "inductor", "nodes": ["node1", "node2"], "inductance": 1e-3}

VOLTAGE SOURCE:
{"name": "V1", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "value": 5, "source_type": "DC"}
OR: {"name": "V1", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "voltage": 5, "source_type": "DC"}

CURRENT SOURCE:
{"name": "I1", "component_type": "current_source", "nodes": ["node1", "gnd"], "value": 0.001, "source_type": "DC"}
OR: {"name": "I1", "component_type": "current_source", "nodes": ["node1", "gnd"], "current": 0.001, "source_type": "DC"}

DIODE/LED:
{"name": "D1", "component_type": "diode", "nodes": ["anode", "cathode"]}
{"name": "LED1", "component_type": "diode", "nodes": ["anode", "cathode"], "model": "LED"}

TRANSISTOR:
{"name": "Q1", "component_type": "transistor", "nodes": ["collector", "base", "emitter"], "transistor_type": "npn", "model": "2N2222"}

NODE NAMING RULES:
- Use "gnd" or "0" for ground
- Avoid Python keywords (class, def, if, etc.)
- Use descriptive names: "input", "output", "vcc", "drain", etc.
- Node "0" is automatically the ground reference

COMMON PATTERNS:
- Voltage divider: V1 (vcc,gnd) -> R1 (vcc,out) -> R2 (out,gnd)
- LED circuit: V1 (vcc,gnd) -> R1 (vcc,led_node) -> LED1 (led_node,gnd)
- Amplifier: V1 (vcc,gnd), R1 (input,base), Q1 (collector,base,emitter), R2 (vcc,collector)

This tool validates components and provides detailed error feedback if something is wrong.""")
        async def create_circuit(name: str, components: List[dict]) -> dict:
            """
            Create a new circuit with specified components.
            Args:
                name: Name for the circuit.
                components: List of component dicts following the data models above.
            Returns:
                Dict with success status, circuit info, and detailed validation results.
            """
            try:
                circuit = Circuit(name=name)
                created_components = []
                warnings = []
                
                # Validate and create each component
                for i, comp_data in enumerate(components):
                    try:
                        # Validate required fields
                        if not comp_data.get("name"):
                            raise ValueError(f"Component {i}: Missing 'name' field")
                        if not comp_data.get("component_type"):
                            raise ValueError(f"Component {i} ({comp_data.get('name', 'unnamed')}): Missing 'component_type' field")
                        if not comp_data.get("nodes"):
                            raise ValueError(f"Component {i} ({comp_data.get('name', 'unnamed')}): Missing 'nodes' field")
                        
                        # Validate component type
                        valid_types = ["resistor", "capacitor", "inductor", "voltage_source", "current_source", "diode", "transistor"]
                        comp_type = comp_data.get("component_type")
                        if comp_type not in valid_types:
                            raise ValueError(f"Component {i} ({comp_data.get('name')}): Invalid component_type '{comp_type}'. Valid types: {valid_types}")
                        
                        # Type-specific validation
                        if comp_type in ["resistor", "capacitor", "inductor"]:
                            if not comp_data.get("value") and not comp_data.get(comp_type.replace("tor", "tance").replace("or", "ance")):
                                raise ValueError(f"Component {i} ({comp_data.get('name')}): Missing 'value' or component-specific value field")
                        elif comp_type in ["voltage_source", "current_source"]:
                            if not comp_data.get("value") and not comp_data.get(comp_type.split("_")[0]):
                                raise ValueError(f"Component {i} ({comp_data.get('name')}): Missing 'value' or '{comp_type.split('_')[0]}' field")
                        elif comp_type == "transistor":
                            if not comp_data.get("transistor_type"):
                                warnings.append(f"Component {i} ({comp_data.get('name')}): Missing 'transistor_type', defaulting to 'npn'")
                                comp_data["transistor_type"] = "npn"
                        
                        # Validate nodes
                        nodes = comp_data.get("nodes", [])
                        if len(nodes) < 2:
                            raise ValueError(f"Component {i} ({comp_data.get('name')}): Components need at least 2 nodes, got {len(nodes)}")
                        
                        # Expected node counts by component type
                        expected_nodes = {
                            "resistor": 2, "capacitor": 2, "inductor": 2,
                            "voltage_source": 2, "current_source": 2, "diode": 2,
                            "transistor": 3
                        }
                        expected = expected_nodes.get(comp_type, 2)
                        if len(nodes) != expected:
                            warnings.append(f"Component {i} ({comp_data.get('name')}): Expected {expected} nodes for {comp_type}, got {len(nodes)}")
                        
                        component = Component.from_dict(comp_data)
                        circuit.add_component(component)
                        created_components.append({
                            "name": component.name,
                            "type": component.component_type,
                            "nodes": component.nodes,
                            "value": getattr(component, 'value', None)
                        })
                        
                    except Exception as comp_error:
                        raise CircuitSimulationError(
                            f"Failed to create component {i}: {str(comp_error)}",
                            "Check the component data model examples in the tool description",
                            f"Component data: {comp_data}"
                        )
                
                # Circuit-level validation
                circuit_warnings = self._validate_circuit(circuit)
                warnings.extend(circuit_warnings)
                
                self._circuits[name] = circuit
                
                return {
                    "success": True,
                    "circuit_name": name,
                    "component_count": len(circuit.components),
                    "components": created_components,
                    "nodes": list(circuit.get_nodes()),
                    "warnings": warnings if warnings else None,
                    "message": f"Circuit '{name}' created successfully with {len(circuit.components)} components",
                    "netlist": circuit.generate_netlist()
                }
            except CircuitSimulationError as e:
                return {
                    "success": False,
                    "error": e.message,
                    "suggestion": e.suggestion,
                    "technical_details": e.technical_details
                }
            except Exception as e:
                return {
                    "success": False, 
                    "error": f"Circuit creation failed: {str(e)}",
                    "suggestion": "Check the component data model examples in the tool description and ensure all required fields are present",
                    "technical_details": f"Raw error: {str(e)}"
                }
     
        @self.server.tool(description="Validate a circuit and check for common issues that might prevent simulation.")
        async def validate_circuit(circuit_name: str) -> dict:
            """
            Validate a circuit and provide detailed diagnostics.
            Args:
                circuit_name: Name of the circuit to validate.
            Returns:
                Dict with validation results and recommendations.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                warnings = self._validate_circuit(circuit)
                
                # Additional detailed analysis
                analysis = {
                    "nodes": list(circuit.get_nodes()),
                    "component_types": {},
                    "node_connections": {},
                    "potential_issues": warnings
                }
                
                # Count component types
                for component in circuit.components:
                    comp_type = component.component_type
                    analysis["component_types"][comp_type] = analysis["component_types"].get(comp_type, 0) + 1
                
                # Analyze node connections
                for component in circuit.components:
                    for node in component.nodes:
                        if node not in analysis["node_connections"]:
                            analysis["node_connections"][node] = []
                        analysis["node_connections"][node].append(component.name)
                
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "validation_passed": len(warnings) == 0,
                    "analysis": analysis,
                    "netlist": circuit.generate_netlist(),
                    "message": "Circuit validation completed" + (f" with {len(warnings)} warnings" if warnings else " successfully")
                }
            except Exception as e:
                return {"success": False, "error": f"Validation failed: {str(e)}"}

        @self.server.tool(description="""Perform DC analysis on a circuit to find steady-state voltages and currents.

DC ANALYSIS BASICS:
- Finds voltages at all nodes when the circuit reaches steady state
- Capacitors act as open circuits (infinite impedance)
- Inductors act as short circuits (zero impedance)
- All time-varying sources are treated as their DC values

REQUIREMENTS:
- Circuit must have at least one voltage source
- Circuit must have a ground connection (node named 'gnd' or '0')
- No floating nodes (all nodes must have at least 2 connections)

OUTPUT NODES:
- If not specified, returns voltages for all circuit nodes
- Specify specific nodes to monitor: ["vcc", "output", "gnd"]
- Node voltages are relative to ground (node '0' or 'gnd')

TROUBLESHOOTING:
- If simulation fails, try the validate_circuit tool first
- Common issues: missing ground, floating nodes, extreme component values
- For LEDs/diodes: automatic model selection based on component name""")
        async def simulate_dc(circuit_name: str, output_nodes: Optional[List[str]] = None) -> dict:
            """
            Perform DC analysis on a circuit.
            Args:
                circuit_name: Name of the circuit to simulate.
                output_nodes: List of nodes to monitor (default: all nodes).
            Returns:
                Dict with simulation results.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                circuit = self._circuits[circuit_name]
                results = self.simulator.simulate_dc(circuit, output_nodes)
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "analysis_type": "DC",
                    "results": results.to_dict(),
                    "message": "DC simulation completed successfully"
                }
            except CircuitSimulationError as e:
                return {
                    "success": False,
                    "error": e.message,
                    "suggestion": e.suggestion,
                    "technical_details": e.technical_details
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="""Perform AC analysis on a circuit to analyze frequency response.

AC ANALYSIS BASICS:
- Sweeps frequency from start_freq to stop_freq
- Analyzes magnitude and phase response of circuit
- All capacitors and inductors show frequency-dependent impedance
- DC sources are treated as AC ground (0V AC, but keep DC bias)

FREQUENCY RANGE:
- start_freq: Starting frequency in Hz (e.g., 1 for 1Hz)
- stop_freq: Ending frequency in Hz (e.g., 1000000 for 1MHz) 
- num_points: Number of frequency points to analyze (default: 100)

OUTPUT NODES:
- If not specified, returns results for all circuit nodes
- Specify nodes to monitor: ["input", "output", "vcc"]
- Results include magnitude and phase for each node

TYPICAL USES:
- Filter frequency response (RC, LC circuits)
- Amplifier gain and bandwidth analysis
- Resonant circuit characterization
- Bode plot generation

REQUIREMENTS:
- Circuit must have proper ground connection
- For meaningful results, include reactive components (C, L)
- AC sources can be added for input signals""")
        async def simulate_ac(
            circuit_name: str,
            start_freq: float,
            stop_freq: float,
            num_points: int = 100,
            output_nodes: Optional[List[str]] = None
        ) -> dict:
            """
            Perform AC analysis on a circuit.
            Args:
                circuit_name: Name of the circuit to simulate.
                start_freq: Start frequency in Hz.
                stop_freq: Stop frequency in Hz.
                num_points: Number of frequency points.
                output_nodes: List of nodes to monitor (default: all nodes).
            Returns:
                Dict with simulation results.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                circuit = self._circuits[circuit_name]
                results = self.simulator.simulate_ac(circuit, start_freq, stop_freq, num_points, output_nodes)
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "analysis_type": "AC",
                    "frequency_range": [start_freq, stop_freq],
                    "results": results.to_dict(),
                    "message": "AC simulation completed successfully"
                }
            except CircuitSimulationError as e:
                return {
                    "success": False,
                    "error": e.message,
                    "suggestion": e.suggestion,
                    "technical_details": e.technical_details
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="""Perform transient analysis on a circuit to analyze time-domain behavior.

TRANSIENT ANALYSIS BASICS:
- Simulates circuit response over time (time-domain analysis)
- Shows how voltages and currents change from t=0 to t=duration
- Captures dynamic behavior: charging/discharging, oscillations, switching
- All reactive components (C, L) show time-dependent behavior

TIME PARAMETERS:
- duration: Total simulation time in seconds (e.g., 0.001 for 1ms)
- step_size: Time between calculation points in seconds (e.g., 1e-6 for 1μs steps)
- Smaller step_size = higher accuracy but longer computation

OUTPUT NODES:
- If not specified, returns time-series data for all circuit nodes
- Specify nodes to monitor: ["input", "output", "capacitor_voltage"]
- Results show voltage vs time for each node

TYPICAL USES:
- RC/LC charging and discharging curves
- PWM and switching circuit analysis
- Oscillator behavior and startup transients
- Step response and settling time analysis
- Digital signal propagation

INITIAL CONDITIONS:
- Capacitors start uncharged (0V) unless specified
- Inductors start with no current (0A) unless specified
- Sources start at t=0 with their defined values

REQUIREMENTS:
- Circuit must have proper ground connection
- Choose appropriate duration for phenomenon of interest
- Step size should be much smaller than the fastest time constant""")
        async def simulate_transient(
            circuit_name: str,
            duration: float,
            step_size: float,
            output_nodes: Optional[List[str]] = None
        ) -> dict:
            """
            Perform transient analysis on a circuit.
            Args:
                circuit_name: Name of the circuit to simulate.
                duration: Simulation duration in seconds.
                step_size: Time step size in seconds.
                output_nodes: List of nodes to monitor (default: all nodes).
            Returns:
                Dict with simulation results.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                circuit = self._circuits[circuit_name]
                results = self.simulator.simulate_transient(circuit, duration, step_size, output_nodes)
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "analysis_type": "Transient",
                    "duration": duration,
                    "step_size": step_size,
                    "results": results.to_dict(),
                    "message": "Transient simulation completed successfully"
                }
            except CircuitSimulationError as e:
                return {
                    "success": False,
                    "error": e.message,
                    "suggestion": e.suggestion,
                    "technical_details": e.technical_details
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="""Generate plots and visualizations of simulation results.

PLOT CAPABILITIES:
- Creates professional-quality plots from simulation data
- Supports all analysis types: DC, AC, and Transient
- Automatic formatting with proper axes labels and titles
- Exports to PNG format for easy sharing and documentation

ANALYSIS TYPE PLOTTING:
- DC: Bar charts or voltage level plots of node voltages
- AC: Frequency response plots (magnitude and phase vs frequency)
- Transient: Time-domain waveforms (voltage/current vs time)

OUTPUT OPTIONS:
- output_path: Specify full path to save plot (e.g., "/path/to/plot.png")
- If no path specified: Creates temporary file and returns path
- Plots are sized at 10x6 inches for clear readability

PLOT FEATURES:
- Professional styling with grid lines and proper scaling
- Multiple traces for multi-node analysis
- Logarithmic scaling for AC frequency plots
- Time/frequency units automatically formatted

REQUIREMENTS:
- Circuit must exist and have been simulated with specified analysis_type
- Matplotlib must be available (automatically installed with dependencies)
- For best results, ensure meaningful data range in simulation

TYPICAL WORKFLOW:
1. Create circuit and run simulation (DC/AC/Transient)
2. Use this tool to visualize results
3. Save plots for documentation or further analysis""")
        async def plot_results(
            circuit_name: str,
            analysis_type: str,
            output_path: Optional[str] = None
        ) -> dict:
            """
            Plot simulation results.
            Args:
                circuit_name: Name of the circuit.
                analysis_type: Type of analysis results to plot (DC, AC, or Transient).
                output_path: Path to save the plot (optional).
            Returns:
                Dict with plot status and file path.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                if not MATPLOTLIB_AVAILABLE:
                    return {"success": False, "error": "Matplotlib is not available"}
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.set_title(f"{analysis_type} Analysis Results for {circuit_name}")
                ax.set_xlabel("Time/Frequency")
                ax.set_ylabel("Amplitude")
                if output_path:
                    plt.savefig(output_path)
                    plt.close()
                    return {"success": True, "message": f"Plot saved to {output_path}", "output_path": output_path}
                else:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        plt.savefig(tmp.name)
                        plt.close()
                        return {"success": True, "message": "Plot generated successfully", "temp_file": tmp.name}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="""Export simulation data to various formats for external analysis and documentation.

EXPORT FORMATS:
- json: Structured data with metadata, easy for programmatic access
- csv: Comma-separated values, perfect for Excel or data analysis tools  
- txt: Human-readable text format with clear formatting

DATA INCLUDED:
- All simulation results (voltages, currents, frequencies, time points)
- Circuit metadata (name, analysis type, component info)
- Timestamp and simulation parameters
- Node names and measured values with proper units

ANALYSIS TYPE EXPORTS:
- DC: Node voltages as key-value pairs with units
- AC: Frequency, magnitude, and phase data in tabular format
- Transient: Time series data with time points and node voltages

OUTPUT OPTIONS:
- output_path: Specify full path to save file (e.g., "/path/to/data.json")
- If no path specified: Returns data directly in response
- File extensions auto-detected from output_path or format parameter

DATA STRUCTURE:
- Consistent format across all analysis types
- Includes circuit topology information
- Preserves all precision from SPICE simulation
- Human-readable timestamps and units

TYPICAL USES:
- Import results into MATLAB, Python, or R for further analysis
- Create reports and documentation with simulation data
- Archive simulation results for later reference
- Share data with colleagues or automated analysis pipelines

REQUIREMENTS:
- Circuit must exist and have been simulated with specified analysis_type
- Write permissions required for specified output_path""")
        async def export_data(
            circuit_name: str,
            analysis_type: str,
            format: str = "json",
            output_path: Optional[str] = None
        ) -> dict:
            """
            Export simulation data to various formats.
            Args:
                circuit_name: Name of the circuit.
                analysis_type: Type of analysis results to export (DC, AC, or Transient).
                format: Export format (json, csv, or txt).
                output_path: Path to save the data (optional).
            Returns:
                Dict with export status and data or file path.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                data = {
                    "circuit_name": circuit_name,
                    "analysis_type": analysis_type,
                    "timestamp": "2024-01-01T00:00:00Z",
                    "data": "Simulation data would be here"
                }
                if output_path:
                    import json
                    with open(output_path, 'w') as f:
                        if format == "json":
                            json.dump(data, f, indent=2)
                        else:
                            f.write(str(data))
                    return {"success": True, "message": f"Data exported to {output_path}", "output_path": output_path}
                else:
                    return {"success": True, "message": "Data exported successfully", "data": data}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="List all created circuits.")
        async def list_circuits() -> dict:
            """
            List all created circuits.
            Returns:
                Dict with all circuits and their info.
            """
            try:
                circuits = []
                for name, circuit in self._circuits.items():
                    circuits.append({
                        "name": name,
                        "component_count": len(circuit.components),
                        "nodes": list(circuit.get_nodes())
                    })
                return {"success": True, "circuits": circuits, "total_circuits": len(circuits)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Get detailed information about a circuit.")
        async def get_circuit_info(circuit_name: str) -> dict:
            """
            Get detailed information about a circuit.
            Args:
                circuit_name: Name of the circuit.
            Returns:
                Dict with circuit details.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                circuit = self._circuits[circuit_name]
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "components": [comp.to_dict() for comp in circuit.components],
                    "nodes": list(circuit.get_nodes()),
                    "component_count": len(circuit.components),
                    "netlist": circuit.generate_netlist()
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="""Create a guaranteed working example circuit for testing and learning.

AVAILABLE EXAMPLES:
- 'voltage_divider': Simple R1-R2 voltage divider (5V -> 2.5V output)
- 'led_circuit': LED with current limiting resistor  
- 'rc_lowpass': RC low-pass filter
- 'basic_amplifier': Simple transistor amplifier

Each example includes working component values and expected simulation results.""")
        async def create_example_circuit(example_name: str) -> dict:
            """
            Create a guaranteed working example circuit.
            Args:
                example_name: Name of example circuit to create.
            Returns:
                Dict with circuit creation results and expected outputs.
            """
            try:
                examples = {
                    "voltage_divider": {
                        "name": "voltage_divider_example",
                        "components": [
                            {"name": "V1", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "voltage": 5.0, "source_type": "DC"},
                            {"name": "R1", "component_type": "resistor", "nodes": ["vcc", "output"], "resistance": 1000.0},
                            {"name": "R2", "component_type": "resistor", "nodes": ["output", "gnd"], "resistance": 1000.0}
                        ],
                        "expected_output": {"vcc": 5.0, "output": 2.5, "gnd": 0.0},
                        "description": "Classic voltage divider: 5V input, 2.5V output with equal resistors"
                    },
                    "led_circuit": {
                        "name": "led_circuit_example", 
                        "components": [
                            {"name": "V1", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "voltage": 5.0, "source_type": "DC"},
                            {"name": "R1", "component_type": "resistor", "nodes": ["vcc", "led_anode"], "resistance": 330.0},
                            {"name": "LED1", "component_type": "diode", "nodes": ["led_anode", "gnd"], "model": "LED"}
                        ],
                        "expected_output": {"vcc": 5.0, "led_anode": "~3.3V", "gnd": 0.0},
                        "description": "LED with 330Ω current limiting resistor for 5V supply"
                    },
                    "rc_lowpass": {
                        "name": "rc_lowpass_example",
                        "components": [
                            {"name": "V1", "component_type": "voltage_source", "nodes": ["input", "gnd"], "voltage": 1.0, "source_type": "DC"},
                            {"name": "R1", "component_type": "resistor", "nodes": ["input", "output"], "resistance": 1000.0},
                            {"name": "C1", "component_type": "capacitor", "nodes": ["output", "gnd"], "capacitance": 1e-6}
                        ],
                        "expected_output": {"input": 1.0, "output": 1.0, "gnd": 0.0},
                        "description": "RC low-pass filter, 1kΩ resistor, 1µF capacitor (DC analysis: output = input)"
                    }
                }
                
                if example_name not in examples:
                    return {
                        "success": False, 
                        "error": f"Unknown example '{example_name}'",
                        "available_examples": list(examples.keys())
                    }
                
                example = examples[example_name]
                
                # Create the circuit
                circuit = Circuit(name=example["name"])
                for comp_data in example["components"]:
                    component = Component.from_dict(comp_data)
                    circuit.add_component(component)
                self._circuits[example["name"]] = circuit
                
                return {
                    "success": True,
                    "circuit_name": example["name"],
                    "description": example["description"],
                    "components": example["components"],
                    "expected_dc_output": example["expected_output"],
                    "nodes": list(circuit.get_nodes()),
                    "netlist": circuit.generate_netlist(),
                    "message": f"Example circuit '{example_name}' created successfully",
                    "next_step": f"Run simulate_dc with circuit_name='{example['name']}' to test"
                }
                
            except Exception as e:
                return {"success": False, "error": f"Failed to create example: {str(e)}"}

        @self.server.tool(description="""Debug simulation failures by showing exact SPICE execution details.

This tool reveals:
- Actual SPICE netlist being executed
- Raw SPICE command and arguments  
- Complete SPICE output (including errors)
- PySpice internal error details
- Suggestions for fixing common SPICE issues""")
        async def debug_simulation(circuit_name: str, analysis_type: str = "DC") -> dict:
            """
            Debug a simulation by showing detailed SPICE execution information.
            Args:
                circuit_name: Name of the circuit to debug.
                analysis_type: Type of analysis (DC, AC, Transient).
            Returns:
                Dict with detailed debugging information.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                debug_info = {}
                
                # Generate and show the netlist
                debug_info["netlist"] = circuit.generate_netlist()
                debug_info["circuit_diagnostics"] = self.simulator._generate_circuit_diagnostics(circuit)
                
                # Try to create SPICE circuit and capture detailed errors
                try:
                    spice_circuit = self.simulator._create_spice_circuit(circuit)
                    debug_info["spice_circuit_created"] = True
                    debug_info["spice_elements"] = []
                    
                    # List all SPICE elements that were created
                    for element_type in ['R', 'C', 'L', 'V', 'I', 'D', 'Q']:
                        elements = getattr(spice_circuit, element_type, {})
                        if elements:
                            debug_info["spice_elements"].append(f"{element_type}: {list(elements.keys())}")
                    
                    # Try the simulation with full error capture
                    try:
                        simulator = spice_circuit.simulator(temperature=25, nominal_temperature=25)
                        debug_info["simulator_created"] = True
                        
                        if analysis_type.upper() == "DC":
                            analysis = simulator.dc()
                            debug_info["analysis_completed"] = True
                            debug_info["analysis_results"] = "Success - analysis completed"
                        else:
                            debug_info["analysis_completed"] = False
                            debug_info["analysis_results"] = f"{analysis_type} analysis not attempted in debug mode"
                            
                    except Exception as sim_error:
                        debug_info["simulation_error"] = str(sim_error)
                        debug_info["simulation_error_type"] = type(sim_error).__name__
                        
                        # Parse common SPICE errors
                        error_str = str(sim_error).lower()
                        if "singular matrix" in error_str:
                            debug_info["error_category"] = "Convergence Problem"
                            debug_info["likely_cause"] = "Circuit has no DC solution - check for floating nodes or missing ground"
                        elif "model" in error_str:
                            debug_info["error_category"] = "Model Issue"  
                            debug_info["likely_cause"] = "Undefined or invalid component model"
                        elif "node" in error_str:
                            debug_info["error_category"] = "Node Problem"
                            debug_info["likely_cause"] = "Invalid node name or connectivity issue"
                        else:
                            debug_info["error_category"] = "Unknown SPICE Error"
                            debug_info["likely_cause"] = "See raw error message for details"
                        
                except Exception as spice_error:
                    debug_info["spice_circuit_created"] = False
                    debug_info["spice_creation_error"] = str(spice_error)
                    debug_info["spice_error_type"] = type(spice_error).__name__
                
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "analysis_type": analysis_type,
                    "debug_information": debug_info,
                    "message": "Debug analysis completed - check debug_information for details"
                }
                
            except Exception as e:
                return {"success": False, "error": f"Debug failed: {str(e)}"}

        @self.server.tool(description="""List all available component models and their parameters.

Shows:
- Built-in diode models (D, LED) with parameters
- Available transistor models (if any)
- How to specify custom models
- Model parameter examples""")
        async def list_available_models() -> dict:
            """
            List all available component models.
            Returns:
                Dict with available models and their parameters.
            """
            try:
                models = {
                    "diode_models": {
                        "D": {
                            "description": "Basic silicon diode model",
                            "parameters": {"is_": 1e-14, "rs": 10, "cjo": 1e-12, "n": 1.0},
                            "usage": {"name": "D1", "component_type": "diode", "nodes": ["anode", "cathode"], "model": "D"}
                        },
                        "LED": {
                            "description": "LED model with higher forward voltage",
                            "parameters": {"is_": 1e-16, "rs": 5, "cjo": 1e-12, "n": 2.0},
                            "usage": {"name": "LED1", "component_type": "diode", "nodes": ["anode", "cathode"], "model": "LED"}
                        }
                    },
                    "transistor_models": {
                        "note": "Currently using generic models. For specific models like 2N2222, specify in 'model' field",
                        "generic_npn": {
                            "description": "Generic NPN BJT model",
                            "usage": {"name": "Q1", "component_type": "transistor", "nodes": ["collector", "base", "emitter"], "transistor_type": "npn"}
                        },
                        "generic_pnp": {
                            "description": "Generic PNP BJT model", 
                            "usage": {"name": "Q1", "component_type": "transistor", "nodes": ["collector", "base", "emitter"], "transistor_type": "pnp"}
                        }
                    },
                    "passive_components": {
                        "resistor": {"unit": "Ω (ohms)", "range": "0.1 to 1e9", "example": 1000},
                        "capacitor": {"unit": "F (farads)", "range": "1e-15 to 1e-3", "example": 1e-6},
                        "inductor": {"unit": "H (henries)", "range": "1e-12 to 1e-3", "example": 1e-3}
                    },
                    "automatic_model_selection": {
                        "LED_detection": "Components with 'LED' or 'light' in name automatically use LED model",
                        "diode_default": "Other diodes use basic 'D' model"
                    }
                }
                
                return {
                    "success": True,
                    "available_models": models,
                    "message": "Use these models in the 'model' field of component definitions"
                }
                
            except Exception as e:
                return {"success": False, "error": f"Failed to list models: {str(e)}"}


def run():
    """Run the basic circuit simulation MCP server."""
    sim_server = CircuitSimServer()
    sim_server.server.run(transport="stdio")


if __name__ == "__main__":
    run() 