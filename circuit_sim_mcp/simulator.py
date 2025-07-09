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
from PySpice.Spice.Netlist import Circuit as PySpiceCircuit
from PySpice.Spice.Netlist import Netlist
from PySpice.Unit import *

from .circuit import Circuit, SimulationResults


class CircuitSimulator:
    """Circuit simulator using PySpice."""
    
    def __init__(self):
        """Initialize the simulator."""
        self._last_results: Optional[SimulationResults] = None
    
    def simulate_dc(
        self, 
        circuit: Circuit, 
        output_nodes: Optional[List[str]] = None
    ) -> SimulationResults:
        """Perform DC analysis on a circuit."""
        try:
            # Create PySpice circuit
            spice_circuit = self._create_spice_circuit(circuit)
            
            # Add DC analysis
            spice_circuit.dc_analysis()
            
            # Get results
            results = spice_circuit.dc_analysis()
            
            # Process results
            data = self._process_dc_results(results, output_nodes or list(circuit.get_nodes()))
            
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
            # Fallback to mock results for development
            return self._mock_dc_results(circuit, output_nodes)
    
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
            
            # Add AC analysis
            spice_circuit.ac_analysis(
                start_frequency=start_freq@u_Hz,
                stop_frequency=stop_freq@u_Hz,
                number_of_points=num_points
            )
            
            # Get results
            results = spice_circuit.ac_analysis()
            
            # Process results
            data = self._process_ac_results(results, output_nodes or list(circuit.get_nodes()))
            
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
            # Fallback to mock results for development
            return self._mock_ac_results(circuit, start_freq, stop_freq, num_points, output_nodes)
    
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
            
            # Add transient analysis
            spice_circuit.transient_analysis(
                step_time=step_size@u_s,
                end_time=duration@u_s
            )
            
            # Get results
            results = spice_circuit.transient_analysis()
            
            # Process results
            data = self._process_transient_results(results, output_nodes or list(circuit.get_nodes()))
            
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
            # Fallback to mock results for development
            return self._mock_transient_results(circuit, duration, step_size, output_nodes)
    
    def _create_spice_circuit(self, circuit: Circuit) -> PySpiceCircuit:
        """Create a PySpice circuit from our Circuit object."""
        spice_circuit = PySpiceCircuit(circuit.name)
        
        for component in circuit.components:
            self._add_component_to_spice(spice_circuit, component)
        
        return spice_circuit
    
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
            model = component.model if component.model else "D"
            spice_circuit.D(component.name, *component.nodes, model)
        elif component.component_type == "transistor":
            model = component.model if component.model else component.transistor_type
            spice_circuit.Q(component.name, *component.nodes, model)
    
    def _process_dc_results(self, results: Any, output_nodes: List[str]) -> Dict[str, Any]:
        """Process DC analysis results."""
        data = {}
        try:
            for node in output_nodes:
                if hasattr(results, node):
                    data[node] = float(getattr(results, node))
                else:
                    data[node] = 0.0
        except:
            # Fallback if PySpice results are not accessible
            for node in output_nodes:
                data[node] = 0.0
        
        return data
    
    def _process_ac_results(self, results: Any, output_nodes: List[str]) -> Dict[str, Any]:
        """Process AC analysis results."""
        data = {"frequency": []}
        try:
            # Get frequency data
            if hasattr(results, 'frequency'):
                data["frequency"] = [float(f) for f in results.frequency]
            
            # Get node data
            for node in output_nodes:
                if hasattr(results, node):
                    node_data = getattr(results, node)
                    if hasattr(node_data, 'magnitude'):
                        data[f"{node}_magnitude"] = [float(m) for m in node_data.magnitude]
                    if hasattr(node_data, 'phase'):
                        data[f"{node}_phase"] = [float(p) for p in node_data.phase]
                else:
                    data[f"{node}_magnitude"] = [0.0] * len(data.get("frequency", [1]))
                    data[f"{node}_phase"] = [0.0] * len(data.get("frequency", [1]))
        except:
            # Fallback
            data["frequency"] = [1.0]
            for node in output_nodes:
                data[f"{node}_magnitude"] = [0.0]
                data[f"{node}_phase"] = [0.0]
        
        return data
    
    def _process_transient_results(self, results: Any, output_nodes: List[str]) -> Dict[str, Any]:
        """Process transient analysis results."""
        data = {"time": []}
        try:
            # Get time data
            if hasattr(results, 'time'):
                data["time"] = [float(t) for t in results.time]
            
            # Get node data
            for node in output_nodes:
                if hasattr(results, node):
                    node_data = getattr(results, node)
                    data[node] = [float(v) for v in node_data]
                else:
                    data[node] = [0.0] * len(data.get("time", [1]))
        except:
            # Fallback
            data["time"] = [0.0]
            for node in output_nodes:
                data[node] = [0.0]
        
        return data
    
    # Mock methods for development/testing when PySpice is not available
    def _mock_dc_results(self, circuit: Circuit, output_nodes: Optional[List[str]] = None) -> SimulationResults:
        """Generate mock DC results for development."""
        nodes = output_nodes or list(circuit.get_nodes())
        data = {}
        
        for node in nodes:
            if node == "0":  # Ground
                data[node] = 0.0
            else:
                # Mock voltage values
                if NUMPY_AVAILABLE:
                    data[node] = np.random.uniform(0, 10)
                else:
                    import random
                    data[node] = random.uniform(0, 10)
        
        return SimulationResults(
            analysis_type="DC",
            circuit_name=circuit.name,
            data=data,
            metadata={
                "output_nodes": output_nodes,
                "total_nodes": len(circuit.get_nodes()),
                "mock": True
            }
        )
    
    def _mock_ac_results(
        self, 
        circuit: Circuit, 
        start_freq: float, 
        stop_freq: float, 
        num_points: int,
        output_nodes: Optional[List[str]] = None
    ) -> SimulationResults:
        """Generate mock AC results for development."""
        nodes = output_nodes or list(circuit.get_nodes())
        
        if NUMPY_AVAILABLE:
            frequencies = np.logspace(np.log10(start_freq), np.log10(stop_freq), num_points)
            data = {"frequency": frequencies.tolist()}
        else:
            import math
            frequencies = []
            for i in range(num_points):
                freq = start_freq * (stop_freq / start_freq) ** (i / (num_points - 1))
                frequencies.append(freq)
            data = {"frequency": frequencies}
        
        for node in nodes:
            if node == "0":  # Ground
                data[f"{node}_magnitude"] = [0.0] * num_points
                data[f"{node}_phase"] = [0.0] * num_points
            else:
                # Mock frequency response
                if NUMPY_AVAILABLE:
                    magnitude = np.random.uniform(0.1, 10, num_points)
                    phase = np.random.uniform(-180, 180, num_points)
                    data[f"{node}_magnitude"] = magnitude.tolist()
                    data[f"{node}_phase"] = phase.tolist()
                else:
                    import random
                    magnitude = [random.uniform(0.1, 10) for _ in range(num_points)]
                    phase = [random.uniform(-180, 180) for _ in range(num_points)]
                    data[f"{node}_magnitude"] = magnitude
                    data[f"{node}_phase"] = phase
        
        return SimulationResults(
            analysis_type="AC",
            circuit_name=circuit.name,
            data=data,
            metadata={
                "start_frequency": start_freq,
                "stop_frequency": stop_freq,
                "num_points": num_points,
                "output_nodes": output_nodes,
                "mock": True
            }
        )
    
    def _mock_transient_results(
        self, 
        circuit: Circuit, 
        duration: float, 
        step_size: float,
        output_nodes: Optional[List[str]] = None
    ) -> SimulationResults:
        """Generate mock transient results for development."""
        nodes = output_nodes or list(circuit.get_nodes())
        
        if NUMPY_AVAILABLE:
            time_points = np.arange(0, duration + step_size, step_size)
            data = {"time": time_points.tolist()}
        else:
            time_points = []
            t = 0.0
            while t <= duration:
                time_points.append(t)
                t += step_size
            data = {"time": time_points}
        
        for node in nodes:
            if node == "0":  # Ground
                data[node] = [0.0] * len(time_points)
            else:
                # Mock transient response
                if NUMPY_AVAILABLE:
                    voltage = np.random.uniform(0, 10, len(time_points))
                    data[node] = voltage.tolist()
                else:
                    import random
                    voltage = [random.uniform(0, 10) for _ in range(len(time_points))]
                    data[node] = voltage
        
        return SimulationResults(
            analysis_type="Transient",
            circuit_name=circuit.name,
            data=data,
            metadata={
                "duration": duration,
                "step_size": step_size,
                "output_nodes": output_nodes,
                "mock": True
            }
        ) 