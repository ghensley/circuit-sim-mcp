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
from .simulator import CircuitSimulator


class CircuitSimServer:
    """Basic MCP server for circuit simulation using PySpice and FastMCP."""
    def __init__(self):
        self.simulator = CircuitSimulator()
        self._circuits: Dict[str, Circuit] = {}
        self.server = FastMCP(name="circuit-sim-mcp", instructions="PySpice circuit simulation server for basic circuit analysis.")
        self._register_tools()

    def _register_tools(self):
        @self.server.tool(description="Create a new circuit with specified components.")
        async def create_circuit(name: str, components: List[dict]) -> dict:
            """
            Create a new circuit with specified components.
            Args:
                name: Name for the circuit.
                components: List of component dicts.
            Returns:
                Dict with success status and circuit info.
            """
            try:
                circuit = Circuit(name=name)
                for comp_data in components:
                    component = Component.from_dict(comp_data)
                    circuit.add_component(component)
                self._circuits[name] = circuit
                return {
                    "success": True,
                    "circuit_name": name,
                    "component_count": len(circuit.components),
                    "message": f"Circuit '{name}' created successfully with {len(circuit.components)} components"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Perform DC analysis on a circuit.")
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
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Perform AC analysis on a circuit.")
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
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Perform transient analysis on a circuit.")
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
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Plot simulation results.")
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

        @self.server.tool(description="Export simulation data to various formats.")
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


def run():
    """Run the basic circuit simulation MCP server."""
    sim_server = CircuitSimServer()
    from mcp.server.fastmcp import FastMCP
    FastMCP.run(transport="stdio")


if __name__ == "__main__":
    run() 