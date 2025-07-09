"""Enhanced component models based on datasheet specifications."""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .circuit import Component


@dataclass
class ComponentDatasheet:
    """Datasheet information for a component."""
    part_number: str
    manufacturer: str
    description: str
    parameters: Dict[str, Any]
    spice_model: Optional[str] = None
    operating_conditions: Optional[Dict[str, Any]] = None
    package_info: Optional[Dict[str, str]] = None


class DatasheetComponentLibrary:
    """Library of components with datasheet-based models."""
    
    def __init__(self):
        self.components: Dict[str, ComponentDatasheet] = {}
        self.load_component_library()
    
    def load_component_library(self):
        """Load component library from JSON files."""
        library_path = Path(__file__).parent / "component_library"
        if library_path.exists():
            for json_file in library_path.glob("*.json"):
                self.load_component_file(json_file)
    
    def load_component_file(self, file_path: Path):
        """Load components from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                for component_data in data.get('components', []):
                    datasheet = ComponentDatasheet(**component_data)
                    self.components[datasheet.part_number] = datasheet
        except Exception as e:
            print(f"Error loading component file {file_path}: {e}")
    
    def get_component(self, part_number: str) -> Optional[ComponentDatasheet]:
        """Get component datasheet by part number."""
        return self.components.get(part_number.upper())
    
    def search_components(self, 
                         component_type: Optional[str] = None,
                         manufacturer: Optional[str] = None,
                         parameters: Optional[Dict[str, Any]] = None) -> List[ComponentDatasheet]:
        """Search for components matching criteria."""
        results = []
        for component in self.components.values():
            if component_type and component_type.lower() not in component.description.lower():
                continue
            if manufacturer and manufacturer.lower() != component.manufacturer.lower():
                continue
            if parameters:
                match = True
                for param, value in parameters.items():
                    if param not in component.parameters:
                        match = False
                        break
                    # Add parameter matching logic here
                if not match:
                    continue
            results.append(component)
        return results


class OpAmp(Component):
    """Operational Amplifier with datasheet parameters."""
    
    component_type: str = "opamp"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Default op-amp parameters
        self.part_number = data.get('part_number', 'GENERIC_OPAMP')
        self.gain_bandwidth = data.get('gain_bandwidth', 1e6)  # Hz
        self.input_offset_voltage = data.get('input_offset_voltage', 1e-3)  # V
        self.input_bias_current = data.get('input_bias_current', 1e-9)  # A
        self.slew_rate = data.get('slew_rate', 1e6)  # V/s
        self.supply_voltage_min = data.get('supply_voltage_min', -15)  # V
        self.supply_voltage_max = data.get('supply_voltage_max', 15)  # V
        self.common_mode_rejection = data.get('common_mode_rejection', 80)  # dB
        
        # Load datasheet if part number is provided
        if hasattr(self, '_library'):
            self._load_datasheet_parameters()
    
    def _load_datasheet_parameters(self):
        """Load parameters from datasheet library."""
        library = DatasheetComponentLibrary()
        datasheet = library.get_component(self.part_number)
        if datasheet:
            # Update parameters from datasheet
            params = datasheet.parameters
            self.gain_bandwidth = params.get('gain_bandwidth_hz', self.gain_bandwidth)
            self.input_offset_voltage = params.get('input_offset_voltage_v', self.input_offset_voltage)
            self.input_bias_current = params.get('input_bias_current_a', self.input_bias_current)
            self.slew_rate = params.get('slew_rate_v_per_s', self.slew_rate)
            self.supply_voltage_min = params.get('supply_voltage_min_v', self.supply_voltage_min)
            self.supply_voltage_max = params.get('supply_voltage_max_v', self.supply_voltage_max)
            self.common_mode_rejection = params.get('cmrr_db', self.common_mode_rejection)
            
            # Set SPICE model if available
            if datasheet.spice_model:
                self.spice_model = datasheet.spice_model


class MOSFET(Component):
    """MOSFET with datasheet parameters."""
    
    component_type: str = "mosfet"
    
    def __init__(self, **data):
        super().__init__(**data)
        self.part_number = data.get('part_number', 'GENERIC_MOSFET')
        self.mosfet_type = data.get('mosfet_type', 'nmos')  # nmos or pmos
        self.threshold_voltage = data.get('threshold_voltage', 2.0)  # V
        self.drain_source_resistance = data.get('drain_source_resistance', 0.1)  # Ohms
        self.gate_source_capacitance = data.get('gate_source_capacitance', 1e-12)  # F
        self.gate_drain_capacitance = data.get('gate_drain_capacitance', 1e-12)  # F
        self.max_drain_current = data.get('max_drain_current', 1.0)  # A
        self.max_drain_source_voltage = data.get('max_drain_source_voltage', 100)  # V
        self.max_gate_source_voltage = data.get('max_gate_source_voltage', 20)  # V
        
        # Load datasheet parameters
        self._load_datasheet_parameters()
    
    def _load_datasheet_parameters(self):
        """Load MOSFET parameters from datasheet."""
        library = DatasheetComponentLibrary()
        datasheet = library.get_component(self.part_number)
        if datasheet:
            params = datasheet.parameters
            self.threshold_voltage = params.get('vth_v', self.threshold_voltage)
            self.drain_source_resistance = params.get('rds_on_ohms', self.drain_source_resistance)
            self.gate_source_capacitance = params.get('cgs_f', self.gate_source_capacitance)
            self.gate_drain_capacitance = params.get('cgd_f', self.gate_drain_capacitance)
            self.max_drain_current = params.get('id_max_a', self.max_drain_current)
            self.max_drain_source_voltage = params.get('vds_max_v', self.max_drain_source_voltage)
            self.max_gate_source_voltage = params.get('vgs_max_v', self.max_gate_source_voltage)


class DiodeWithDatasheet(Component):
    """Diode with comprehensive datasheet parameters."""
    
    component_type: str = "diode"
    
    def __init__(self, **data):
        super().__init__(**data)
        self.part_number = data.get('part_number', 'GENERIC_DIODE')
        self.forward_voltage = data.get('forward_voltage', 0.7)  # V
        self.reverse_current = data.get('reverse_current', 1e-9)  # A
        self.junction_capacitance = data.get('junction_capacitance', 1e-12)  # F
        self.max_forward_current = data.get('max_forward_current', 1.0)  # A
        self.max_reverse_voltage = data.get('max_reverse_voltage', 100)  # V
        self.recovery_time = data.get('recovery_time', 1e-9)  # s
        self.thermal_resistance = data.get('thermal_resistance', 100)  # K/W
        
        self._load_datasheet_parameters()
    
    def _load_datasheet_parameters(self):
        """Load diode parameters from datasheet."""
        library = DatasheetComponentLibrary()
        datasheet = library.get_component(self.part_number)
        if datasheet:
            params = datasheet.parameters
            self.forward_voltage = params.get('vf_v', self.forward_voltage)
            self.reverse_current = params.get('ir_a', self.reverse_current)
            self.junction_capacitance = params.get('cj_f', self.junction_capacitance)
            self.max_forward_current = params.get('if_max_a', self.max_forward_current)
            self.max_reverse_voltage = params.get('vr_max_v', self.max_reverse_voltage)
            self.recovery_time = params.get('trr_s', self.recovery_time)


def create_datasheet_component(component_type: str, part_number: str, **kwargs) -> Component:
    """Factory function to create components with datasheet parameters."""
    library = DatasheetComponentLibrary()
    datasheet = library.get_component(part_number)
    
    if not datasheet:
        raise ValueError(f"Component {part_number} not found in datasheet library")
    
    # Map component types to classes
    component_classes = {
        'opamp': OpAmp,
        'operational_amplifier': OpAmp,
        'mosfet': MOSFET,
        'transistor': MOSFET,
        'diode': DiodeWithDatasheet,
    }
    
    component_class = component_classes.get(component_type.lower())
    if not component_class:
        raise ValueError(f"Unsupported component type: {component_type}")
    
    # Merge datasheet parameters with user parameters
    combined_params = {**datasheet.parameters, **kwargs}
    combined_params['part_number'] = part_number
    
    return component_class(**combined_params) 