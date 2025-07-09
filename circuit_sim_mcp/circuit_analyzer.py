"""Circuit complexity analysis and datasheet prompting system."""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import Counter

from .circuit import Component


@dataclass
class ComplexityMetrics:
    """Metrics for circuit complexity analysis."""
    component_count: int
    component_types: int
    node_count: int
    active_components: int
    passive_components: int
    power_components: int
    unknown_components: int
    complexity_score: float
    complexity_level: str  # "simple", "moderate", "complex", "very_complex"


@dataclass
class DatasheetPrompt:
    """Prompt for user to upload specific datasheets."""
    component_type: str
    suggested_parts: List[str]
    priority: str  # "critical", "recommended", "optional"
    reason: str
    impact: str
    example_datasheets: List[str]


class CircuitComplexityAnalyzer:
    """Analyzes circuit complexity and suggests datasheet uploads."""
    
    def __init__(self):
        self.complexity_thresholds = {
            "simple": 5,        # <= 5 components
            "moderate": 15,     # 6-15 components  
            "complex": 30,      # 16-30 components
            "very_complex": 30  # > 30 components
        }
        
        self.component_complexity_weights = {
            # Passive components (low complexity)
            "resistor": 1,
            "capacitor": 1,
            "inductor": 2,
            
            # Active components (medium complexity)
            "diode": 2,
            "transistor": 3,
            "mosfet": 3,
            "jfet": 3,
            
            # Complex components (high complexity)
            "opamp": 4,
            "operational_amplifier": 4,
            "comparator": 3,
            "voltage_regulator": 4,
            "microcontroller": 8,
            "fpga": 10,
            "cpu": 12,
            
            # Power components (medium-high complexity)
            "voltage_source": 2,
            "current_source": 2,
            "power_supply": 5,
            "switching_regulator": 6,
            
            # RF/Analog components (high complexity)
            "mixer": 5,
            "oscillator": 4,
            "pll": 6,
            "adc": 5,
            "dac": 5,
            
            # Digital components (variable complexity)
            "logic_gate": 2,
            "flip_flop": 3,
            "counter": 4,
            "memory": 5,
        }
    
    def analyze_circuit_complexity(self, components: List[Component]) -> ComplexityMetrics:
        """Analyze the complexity of a circuit."""
        if not components:
            return ComplexityMetrics(0, 0, 0, 0, 0, 0, 0, 0.0, "simple")
        
        # Count components by type
        component_types = Counter(comp.component_type for comp in components)
        
        # Calculate complexity score
        complexity_score = 0
        active_components = 0
        passive_components = 0
        power_components = 0
        unknown_components = 0
        
        for comp in components:
            comp_type = comp.component_type.lower()
            weight = self.component_complexity_weights.get(comp_type, 3)
            complexity_score += weight
            
            # Categorize components
            if comp_type in ["resistor", "capacitor", "inductor"]:
                passive_components += 1
            elif comp_type in ["voltage_source", "current_source", "power_supply", "switching_regulator"]:
                power_components += 1
            elif comp_type in ["opamp", "transistor", "mosfet", "diode", "microcontroller", "fpga"]:
                active_components += 1
            else:
                unknown_components += 1
        
        # Count unique nodes
        all_nodes = set()
        for comp in components:
            all_nodes.update(comp.nodes)
        node_count = len(all_nodes)
        
        # Add complexity factors
        if node_count > 20:
            complexity_score *= 1.2
        if len(component_types) > 10:
            complexity_score *= 1.1
        if active_components > passive_components:
            complexity_score *= 1.15
        
        # Determine complexity level
        if complexity_score <= self.complexity_thresholds["simple"]:
            level = "simple"
        elif complexity_score <= self.complexity_thresholds["moderate"]:
            level = "moderate"
        elif complexity_score <= self.complexity_thresholds["complex"]:
            level = "complex"
        else:
            level = "very_complex"
        
        return ComplexityMetrics(
            component_count=len(components),
            component_types=len(component_types),
            node_count=node_count,
            active_components=active_components,
            passive_components=passive_components,
            power_components=power_components,
            unknown_components=unknown_components,
            complexity_score=complexity_score,
            complexity_level=level
        )
    
    def generate_datasheet_prompts(self, components: List[Component], complexity: ComplexityMetrics) -> List[DatasheetPrompt]:
        """Generate prompts for datasheet uploads based on circuit analysis."""
        prompts = []
        
        # Analyze components and their needs
        component_analysis = self._analyze_component_needs(components)
        
        # Generate prompts based on complexity and missing datasheets
        for comp_type, analysis in component_analysis.items():
            if analysis["needs_datasheet"]:
                prompt = self._create_datasheet_prompt(comp_type, analysis, complexity)
                if prompt:
                    prompts.append(prompt)
        
        # Sort by priority
        priority_order = {"critical": 0, "recommended": 1, "optional": 2}
        prompts.sort(key=lambda x: priority_order.get(x.priority, 3))
        
        return prompts
    
    def _analyze_component_needs(self, components: List[Component]) -> Dict[str, Dict[str, Any]]:
        """Analyze which components need datasheets."""
        analysis = {}
        
        for comp in components:
            comp_type = comp.component_type.lower()
            
            if comp_type not in analysis:
                analysis[comp_type] = {
                    "count": 0,
                    "has_datasheet": False,
                    "needs_datasheet": False,
                    "part_numbers": [],
                    "complexity_weight": self.component_complexity_weights.get(comp_type, 3)
                }
            
            analysis[comp_type]["count"] += 1
            
            # Check if component has datasheet info
            if hasattr(comp, 'part_number') and comp.part_number not in ['GENERIC', None]:
                analysis[comp_type]["has_datasheet"] = True
                analysis[comp_type]["part_numbers"].append(comp.part_number)
            
            # Determine if datasheet is needed
            if analysis[comp_type]["complexity_weight"] >= 3 and not analysis[comp_type]["has_datasheet"]:
                analysis[comp_type]["needs_datasheet"] = True
        
        return analysis
    
    def _create_datasheet_prompt(self, comp_type: str, analysis: Dict[str, Any], complexity: ComplexityMetrics) -> Optional[DatasheetPrompt]:
        """Create a specific datasheet prompt for a component type."""
        if not analysis["needs_datasheet"]:
            return None
        
        # Define component-specific prompts
        component_prompts = {
            "opamp": {
                "suggested_parts": ["LM741", "LM358", "OP07", "TL071", "OPA2134", "AD8066"],
                "reason": "Op-amps require precise specifications for gain-bandwidth, slew rate, and offset voltage",
                "impact": "Accurate frequency response, stability analysis, and noise calculations",
                "examples": ["LM741.pdf", "OPA2134.pdf", "AD8066.pdf"]
            },
            "mosfet": {
                "suggested_parts": ["IRF540N", "2N7000", "BSS138", "IRF9540N", "Si7021"],
                "reason": "MOSFETs need threshold voltage, Ron, and capacitance specifications",
                "impact": "Proper switching analysis, power dissipation, and timing calculations",
                "examples": ["IRF540N.pdf", "2N7000.pdf", "BSS138.pdf"]
            },
            "transistor": {
                "suggested_parts": ["2N2222", "2N3904", "2N3906", "BC547", "2N2907"],
                "reason": "Transistors require beta, Vbe, and frequency response parameters",
                "impact": "Accurate amplification, switching, and small-signal analysis",
                "examples": ["2N2222.pdf", "2N3904.pdf", "BC547.pdf"]
            },
            "voltage_regulator": {
                "suggested_parts": ["LM7805", "LM317", "AMS1117", "LP2950", "TPS7A47"],
                "reason": "Regulators need dropout voltage, load regulation, and thermal characteristics",
                "impact": "Power supply stability, thermal management, and load capability analysis",
                "examples": ["LM7805.pdf", "LM317.pdf", "AMS1117.pdf"]
            },
            "microcontroller": {
                "suggested_parts": ["ATmega328P", "STM32F103", "PIC16F877A", "ESP32", "Arduino Uno"],
                "reason": "MCUs require I/O characteristics, power consumption, and timing specifications",
                "impact": "Digital interface design, power budgeting, and signal integrity",
                "examples": ["ATmega328P.pdf", "STM32F103.pdf", "ESP32.pdf"]
            },
            "adc": {
                "suggested_parts": ["ADS1115", "MCP3008", "AD7476", "LTC2309", "MAX1247"],
                "reason": "ADCs need resolution, sampling rate, and input impedance specifications",
                "impact": "Accurate signal acquisition, anti-aliasing filter design, and noise analysis",
                "examples": ["ADS1115.pdf", "MCP3008.pdf", "AD7476.pdf"]
            },
            "dac": {
                "suggested_parts": ["DAC0800", "MCP4725", "AD5328", "LTC1257", "MAX5216"],
                "reason": "DACs require resolution, settling time, and output characteristics",
                "impact": "Signal generation accuracy, reconstruction filter design, and linearity analysis",
                "examples": ["MCP4725.pdf", "AD5328.pdf", "MAX5216.pdf"]
            }
        }
        
        prompt_info = component_prompts.get(comp_type)
        if not prompt_info:
            # Generic prompt for unknown components
            prompt_info = {
                "suggested_parts": [f"Generic_{comp_type.upper()}_Part"],
                "reason": f"{comp_type.title()} components benefit from datasheet specifications",
                "impact": "More accurate simulation and design validation",
                "examples": [f"{comp_type}_datasheet.pdf"]
            }
        
        # Determine priority based on complexity and component importance
        if complexity.complexity_level in ["complex", "very_complex"] and analysis["complexity_weight"] >= 4:
            priority = "critical"
        elif complexity.complexity_level in ["moderate", "complex"] and analysis["complexity_weight"] >= 3:
            priority = "recommended"
        else:
            priority = "optional"
        
        return DatasheetPrompt(
            component_type=comp_type,
            suggested_parts=prompt_info["suggested_parts"],
            priority=priority,
            reason=prompt_info["reason"],
            impact=prompt_info["impact"],
            example_datasheets=prompt_info["examples"]
        )
    
    def should_prompt_for_datasheets(self, complexity: ComplexityMetrics) -> bool:
        """Determine if the system should prompt for datasheet uploads."""
        return (
            complexity.complexity_level in ["complex", "very_complex"] or
            complexity.active_components >= 3 or
            complexity.unknown_components >= 2 or
            complexity.complexity_score >= 15
        )
    
    def generate_circuit_analysis_report(self, components: List[Component]) -> Dict[str, Any]:
        """Generate a comprehensive circuit analysis report."""
        complexity = self.analyze_circuit_complexity(components)
        prompts = self.generate_datasheet_prompts(components, complexity)
        should_prompt = self.should_prompt_for_datasheets(complexity)
        
        return {
            "complexity_metrics": {
                "level": complexity.complexity_level,
                "score": complexity.complexity_score,
                "component_count": complexity.component_count,
                "component_types": complexity.component_types,
                "node_count": complexity.node_count,
                "breakdown": {
                    "active": complexity.active_components,
                    "passive": complexity.passive_components,
                    "power": complexity.power_components,
                    "unknown": complexity.unknown_components
                }
            },
            "datasheet_recommendations": {
                "should_prompt": should_prompt,
                "total_prompts": len(prompts),
                "critical_prompts": len([p for p in prompts if p.priority == "critical"]),
                "recommended_prompts": len([p for p in prompts if p.priority == "recommended"]),
                "prompts": [
                    {
                        "component_type": p.component_type,
                        "priority": p.priority,
                        "reason": p.reason,
                        "impact": p.impact,
                        "suggested_parts": p.suggested_parts,
                        "example_datasheets": p.example_datasheets
                    } for p in prompts
                ]
            },
            "recommendations": self._generate_general_recommendations(complexity, prompts)
        }
    
    def _generate_general_recommendations(self, complexity: ComplexityMetrics, prompts: List[DatasheetPrompt]) -> List[str]:
        """Generate general recommendations for the circuit design."""
        recommendations = []
        
        if complexity.complexity_level == "very_complex":
            recommendations.append("This is a very complex circuit. Consider breaking it into smaller subcircuits for easier analysis.")
            recommendations.append("Use datasheet-based components for all active devices to ensure accurate simulation.")
        
        if complexity.active_components > complexity.passive_components * 2:
            recommendations.append("High ratio of active to passive components detected. Pay special attention to power supply design and signal integrity.")
        
        if complexity.node_count > 50:
            recommendations.append("Large number of nodes detected. Consider using hierarchical design or subcircuits.")
        
        if len([p for p in prompts if p.priority == "critical"]) > 0:
            recommendations.append("Critical components detected that require datasheets for accurate simulation.")
        
        if complexity.unknown_components > 0:
            recommendations.append("Unknown component types detected. Consider adding them to the component library.")
        
        return recommendations 