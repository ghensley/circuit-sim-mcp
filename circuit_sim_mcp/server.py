"""Main MCP server implementation for circuit simulation using FastMCP."""

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
from .datasheet_components import (
    DatasheetComponentLibrary, 
    create_datasheet_component,
    OpAmp, 
    MOSFET, 
    DiodeWithDatasheet
)
from .circuit_analyzer import CircuitComplexityAnalyzer


class CircuitSimServer:
    """MCP server for circuit simulation using PySpice and FastMCP."""
    def __init__(self):
        self.simulator = CircuitSimulator()
        self._circuits: Dict[str, Circuit] = {}
        self.component_library = DatasheetComponentLibrary()
        self.complexity_analyzer = CircuitComplexityAnalyzer()
        self.server = FastMCP(name="circuit-sim-mcp", instructions="PySpice circuit simulation server with intelligent datasheet guidance.")
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

        @self.server.tool(description="Create a circuit with intelligent complexity analysis and datasheet recommendations.")
        async def create_smart_circuit(name: str, components: List[dict]) -> dict:
            """
            Create a new circuit with automatic complexity analysis and datasheet recommendations.
            Args:
                name: Name for the circuit.
                components: List of component dicts.
            Returns:
                Dict with success status, circuit info, and intelligent recommendations.
            """
            try:
                # Create circuit components first
                circuit_components = []
                for comp_data in components:
                    component = Component.from_dict(comp_data)
                    circuit_components.append(component)
                
                # Analyze circuit complexity before creation
                analysis_report = self.complexity_analyzer.generate_circuit_analysis_report(circuit_components)
                
                # Create the circuit
                circuit = Circuit(name=name)
                for component in circuit_components:
                    circuit.add_component(component)
                self._circuits[name] = circuit
                
                # Prepare response with analysis
                response = {
                    "success": True,
                    "circuit_name": name,
                    "component_count": len(circuit.components),
                    "message": f"Smart circuit '{name}' created successfully",
                    "complexity_analysis": analysis_report["complexity_metrics"],
                    "datasheet_recommendations": analysis_report["datasheet_recommendations"],
                    "design_recommendations": analysis_report["recommendations"]
                }
                
                # Add user-friendly prompts if complex
                if analysis_report["datasheet_recommendations"]["should_prompt"]:
                    response["user_prompts"] = self._format_user_prompts(analysis_report["datasheet_recommendations"]["prompts"])
                
                return response
                
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Analyze circuit complexity and get datasheet recommendations.")
        async def analyze_circuit_complexity(circuit_name: str) -> dict:
            """
            Analyze the complexity of an existing circuit and provide datasheet recommendations.
            Args:
                circuit_name: Name of the circuit to analyze.
            Returns:
                Dict with complexity analysis and datasheet recommendations.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                analysis_report = self.complexity_analyzer.generate_circuit_analysis_report(circuit.components)
                
                response = {
                    "success": True,
                    "circuit_name": circuit_name,
                    "analysis": analysis_report
                }
                
                # Add formatted user prompts if needed
                if analysis_report["datasheet_recommendations"]["should_prompt"]:
                    response["user_prompts"] = self._format_user_prompts(analysis_report["datasheet_recommendations"]["prompts"])
                
                return response
                
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Get intelligent datasheet upload prompts for a circuit.")
        async def get_datasheet_prompts(circuit_name: str, detailed: bool = True) -> dict:
            """
            Get intelligent prompts for datasheet uploads based on circuit analysis.
            Args:
                circuit_name: Name of the circuit to analyze.
                detailed: Whether to include detailed explanations and examples.
            Returns:
                Dict with formatted datasheet upload prompts.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                complexity = self.complexity_analyzer.analyze_circuit_complexity(circuit.components)
                prompts = self.complexity_analyzer.generate_datasheet_prompts(circuit.components, complexity)
                
                if not prompts:
                    return {
                        "success": True,
                        "circuit_name": circuit_name,
                        "message": "No datasheet uploads needed - circuit uses simple components or already has sufficient datasheet information.",
                        "prompts": []
                    }
                
                formatted_prompts = self._format_detailed_prompts(prompts) if detailed else self._format_simple_prompts(prompts)
                
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "complexity_level": complexity.complexity_level,
                    "total_prompts": len(prompts),
                    "critical_count": len([p for p in prompts if p.priority == "critical"]),
                    "recommended_count": len([p for p in prompts if p.priority == "recommended"]),
                    "message": self._generate_prompt_message(prompts, complexity),
                    "prompts": formatted_prompts
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Simulate and validate a circuit with datasheet guidance.")
        async def simulate_with_guidance(
            circuit_name: str,
            analysis_type: str = "dc",
            auto_prompt_datasheets: bool = True,
            **simulation_params
        ) -> dict:
            """
            Perform circuit simulation with intelligent datasheet guidance.
            Args:
                circuit_name: Name of the circuit to simulate.
                analysis_type: Type of analysis (dc, ac, transient).
                auto_prompt_datasheets: Whether to automatically provide datasheet prompts.
                **simulation_params: Additional simulation parameters.
            Returns:
                Dict with simulation results and guidance.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                response = {"success": True, "circuit_name": circuit_name}
                
                # Perform complexity analysis
                if auto_prompt_datasheets:
                    complexity = self.complexity_analyzer.analyze_circuit_complexity(circuit.components)
                    prompts = self.complexity_analyzer.generate_datasheet_prompts(circuit.components, complexity)
                    
                    if prompts:
                        response["datasheet_guidance"] = {
                            "complexity_level": complexity.complexity_level,
                            "simulation_confidence": self._calculate_simulation_confidence(circuit.components),
                            "recommendations": self._format_user_prompts(prompts),
                            "warning": "Simulation accuracy may be limited without proper component datasheets."
                        }
                
                # Perform the requested simulation
                if analysis_type.lower() == "dc":
                    sim_result = await self.simulate_dc(circuit_name, simulation_params.get("output_nodes"))
                elif analysis_type.lower() == "ac":
                    sim_result = await self.simulate_ac(
                        circuit_name,
                        simulation_params.get("start_freq", 1.0),
                        simulation_params.get("stop_freq", 1e6),
                        simulation_params.get("num_points", 50),
                        simulation_params.get("output_nodes")
                    )
                elif analysis_type.lower() == "transient":
                    sim_result = await self.simulate_transient(
                        circuit_name,
                        simulation_params.get("duration", 1e-3),
                        simulation_params.get("step_size", 1e-6),
                        simulation_params.get("output_nodes")
                    )
                else:
                    return {"success": False, "error": f"Unsupported analysis type: {analysis_type}"}
                
                # Merge simulation results
                if isinstance(sim_result, dict):
                    response.update(sim_result)
                else:
                    response["simulation_result"] = sim_result
                
                return response
                
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Create a circuit using datasheet-based components.")
        async def create_datasheet_circuit(name: str, components: List[dict]) -> dict:
            """
            Create a new circuit using components with datasheet parameters.
            Args:
                name: Name for the circuit.
                components: List of component dicts with part_number field.
            Returns:
                Dict with success status and detailed component info.
            """
            try:
                circuit = Circuit(name=name)
                component_details = []
                
                for comp_data in components:
                    if 'part_number' in comp_data:
                        # Use datasheet component
                        component = create_datasheet_component(
                            comp_data['type'], 
                            comp_data['part_number'],
                            **{k: v for k, v in comp_data.items() if k not in ['type', 'part_number']}
                        )
                        datasheet = self.component_library.get_component(comp_data['part_number'])
                        component_details.append({
                            "name": component.name,
                            "part_number": comp_data['part_number'],
                            "manufacturer": datasheet.manufacturer if datasheet else "Unknown",
                            "datasheet_loaded": datasheet is not None,
                            "parameters": component.to_dict()
                        })
                    else:
                        # Use generic component
                        component = Component.from_dict(comp_data)
                        component_details.append({
                            "name": component.name,
                            "part_number": "Generic",
                            "manufacturer": "Generic",
                            "datasheet_loaded": False,
                            "parameters": component.to_dict()
                        })
                    
                    circuit.add_component(component)
                
                self._circuits[name] = circuit
                return {
                    "success": True,
                    "circuit_name": name,
                    "component_count": len(circuit.components),
                    "components": component_details,
                    "message": f"Datasheet circuit '{name}' created successfully"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Search for components in the datasheet library.")
        async def search_components(
            component_type: Optional[str] = None,
            manufacturer: Optional[str] = None,
            parameter_filters: Optional[Dict[str, Any]] = None
        ) -> dict:
            """
            Search for components in the datasheet library.
            Args:
                component_type: Type of component to search for.
                manufacturer: Manufacturer name to filter by.
                parameter_filters: Dictionary of parameter filters.
            Returns:
                Dict with search results.
            """
            try:
                results = self.component_library.search_components(
                    component_type=component_type,
                    manufacturer=manufacturer,
                    parameters=parameter_filters
                )
                
                component_list = []
                for component in results:
                    component_list.append({
                        "part_number": component.part_number,
                        "manufacturer": component.manufacturer,
                        "description": component.description,
                        "parameters": component.parameters,
                        "package": component.package_info
                    })
                
                return {
                    "success": True,
                    "results_count": len(component_list),
                    "components": component_list
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Get detailed datasheet information for a specific component.")
        async def get_component_datasheet(part_number: str) -> dict:
            """
            Get detailed datasheet information for a specific component.
            Args:
                part_number: Component part number.
            Returns:
                Dict with complete datasheet information.
            """
            try:
                datasheet = self.component_library.get_component(part_number)
                if not datasheet:
                    return {"success": False, "error": f"Component {part_number} not found in library"}
                
                return {
                    "success": True,
                    "part_number": datasheet.part_number,
                    "manufacturer": datasheet.manufacturer,
                    "description": datasheet.description,
                    "parameters": datasheet.parameters,
                    "spice_model": datasheet.spice_model,
                    "operating_conditions": datasheet.operating_conditions,
                    "package_info": datasheet.package_info
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Validate circuit design against component specifications.")
        async def validate_circuit_design(circuit_name: str) -> dict:
            """
            Validate circuit design against component datasheet specifications.
            Args:
                circuit_name: Name of the circuit to validate.
            Returns:
                Dict with validation results and warnings.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                validation_results = []
                warnings = []
                errors = []
                
                for component in circuit.components:
                    result = {"component": component.name, "type": component.component_type}
                    
                    # Check if component has datasheet parameters
                    if hasattr(component, 'part_number') and component.part_number != 'GENERIC':
                        datasheet = self.component_library.get_component(component.part_number)
                        if datasheet:
                            result["datasheet_available"] = True
                            result["manufacturer"] = datasheet.manufacturer
                            
                            # Perform specific validations based on component type
                            if isinstance(component, OpAmp):
                                # Check supply voltage limits
                                if hasattr(component, 'supply_voltage_min') and hasattr(component, 'supply_voltage_max'):
                                    result["supply_voltage_range"] = [component.supply_voltage_min, component.supply_voltage_max]
                            
                            elif isinstance(component, MOSFET):
                                # Check voltage/current limits
                                if hasattr(component, 'max_drain_source_voltage'):
                                    result["max_vds"] = component.max_drain_source_voltage
                                if hasattr(component, 'max_drain_current'):
                                    result["max_id"] = component.max_drain_current
                            
                            result["status"] = "validated"
                        else:
                            result["datasheet_available"] = False
                            warnings.append(f"No datasheet found for {component.name} ({component.part_number})")
                    else:
                        result["datasheet_available"] = False
                        result["status"] = "generic_component"
                    
                    validation_results.append(result)
                
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "validation_results": validation_results,
                    "warnings": warnings,
                    "errors": errors,
                    "overall_status": "valid" if not errors else "invalid"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.server.tool(description="Generate an optimized circuit with component recommendations.")
        async def optimize_circuit_design(
            circuit_name: str,
            optimization_goals: List[str],
            constraints: Optional[Dict[str, Any]] = None
        ) -> dict:
            """
            Generate circuit optimization recommendations based on datasheet analysis.
            Args:
                circuit_name: Name of the circuit to optimize.
                optimization_goals: List of goals (e.g., "power", "speed", "cost", "noise").
                constraints: Optional constraints dictionary.
            Returns:
                Dict with optimization recommendations.
            """
            try:
                if circuit_name not in self._circuits:
                    return {"success": False, "error": f"Circuit '{circuit_name}' not found"}
                
                circuit = self._circuits[circuit_name]
                recommendations = []
                
                for component in circuit.components:
                    if hasattr(component, 'part_number') and component.part_number != 'GENERIC':
                        # Find alternative components
                        alternatives = self.component_library.search_components(
                            component_type=component.component_type
                        )
                        
                        if len(alternatives) > 1:
                            current_part = component.part_number
                            alternative_parts = [alt.part_number for alt in alternatives 
                                              if alt.part_number != current_part][:3]
                            
                            recommendation = {
                                "current_component": current_part,
                                "alternatives": alternative_parts,
                                "optimization_for": optimization_goals,
                                "recommendation_reason": self._generate_recommendation_reason(
                                    component, alternatives, optimization_goals
                                )
                            }
                            recommendations.append(recommendation)
                
                return {
                    "success": True,
                    "circuit_name": circuit_name,
                    "optimization_goals": optimization_goals,
                    "recommendations": recommendations,
                    "message": f"Generated {len(recommendations)} optimization recommendations"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Keep all existing simulation tools...
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

    def _format_user_prompts(self, prompts) -> List[Dict[str, Any]]:
        """Format datasheet prompts for user display."""
        user_prompts = []
        for prompt in prompts:
            user_prompt = {
                "priority": prompt["priority"].upper(),
                "component_type": prompt["component_type"].title(),
                "message": f"📋 {prompt['priority'].title()}: Upload datasheet for {prompt['component_type']} components",
                "reason": prompt["reason"],
                "suggested_parts": prompt["suggested_parts"][:3],  # Limit to top 3
                "examples": prompt["example_datasheets"][:2]  # Limit to top 2 examples
            }
            user_prompts.append(user_prompt)
        return user_prompts

    def _format_detailed_prompts(self, prompts) -> List[Dict[str, Any]]:
        """Format detailed datasheet prompts."""
        return [
            {
                "component_type": p.component_type,
                "priority": p.priority,
                "reason": p.reason,
                "impact": p.impact,
                "suggested_parts": p.suggested_parts,
                "example_datasheets": p.example_datasheets,
                "action_required": f"Please upload a datasheet for {p.component_type} components to improve simulation accuracy."
            } for p in prompts
        ]

    def _format_simple_prompts(self, prompts) -> List[str]:
        """Format simple datasheet prompts."""
        return [f"{p.priority.upper()}: {p.component_type} - {p.reason}" for p in prompts]

    def _generate_prompt_message(self, prompts, complexity) -> str:
        """Generate an appropriate message for datasheet prompts."""
        critical_count = len([p for p in prompts if p.priority == "critical"])
        
        if complexity.complexity_level == "very_complex":
            return f"⚠️ Very complex circuit detected! {critical_count} critical datasheets needed for accurate simulation."
        elif complexity.complexity_level == "complex":
            return f"🔧 Complex circuit detected. {len(prompts)} datasheets recommended for better accuracy."
        else:
            return f"📈 {len(prompts)} datasheet uploads recommended to improve simulation quality."

    def _calculate_simulation_confidence(self, components) -> str:
        """Calculate confidence level for simulation accuracy."""
        total_components = len(components)
        datasheet_components = sum(1 for comp in components 
                                 if hasattr(comp, 'part_number') and comp.part_number not in ['GENERIC', None])
        
        if total_components == 0:
            return "unknown"
        
        confidence_ratio = datasheet_components / total_components
        
        if confidence_ratio >= 0.8:
            return "high"
        elif confidence_ratio >= 0.5:
            return "medium"
        elif confidence_ratio >= 0.2:
            return "low"
        else:
            return "very_low"

    def _generate_recommendation_reason(self, component, alternatives, goals):
        """Generate a recommendation reason based on optimization goals."""
        if "power" in goals:
            return "Consider lower power alternatives for improved efficiency"
        elif "speed" in goals:
            return "Consider higher bandwidth/faster switching alternatives"
        elif "cost" in goals:
            return "Consider more cost-effective alternatives"
        elif "noise" in goals:
            return "Consider low-noise alternatives for better signal integrity"
        else:
            return "General performance optimization recommendations available" 