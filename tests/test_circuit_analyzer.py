"""Test circuit complexity analyzer and datasheet prompting system."""

import pytest
from circuit_sim_mcp.circuit import Component
from circuit_sim_mcp.circuit_analyzer import CircuitComplexityAnalyzer, ComplexityMetrics, DatasheetPrompt


class TestCircuitComplexityAnalyzer:
    """Test the circuit complexity analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CircuitComplexityAnalyzer()
    
    def test_simple_circuit_analysis(self):
        """Test analysis of a simple circuit."""
        components = [
            Component("R1", "resistor", ["n1", "n2"], value=1000.0),
            Component("R2", "resistor", ["n2", "gnd"], value=2000.0),
            Component("V1", "voltage_source", ["n1", "gnd"], value=5.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        
        assert metrics.component_count == 3
        assert metrics.complexity_level == "simple"
        assert metrics.passive_components == 2
        assert metrics.power_components == 1
        assert metrics.active_components == 0
        assert metrics.node_count == 3  # n1, n2, gnd
    
    def test_moderate_circuit_analysis(self):
        """Test analysis of a moderate complexity circuit."""
        components = [
            Component("R1", "resistor", ["in", "out"], value=10000.0),
            Component("R2", "resistor", ["out", "gnd"], value=10000.0),
            Component("C1", "capacitor", ["out", "gnd"], value=1e-6),
            Component("U1", "opamp", ["in", "out", "out", "vcc", "vee"], gain=100000.0),
            Component("VCC", "voltage_source", ["vcc", "gnd"], value=15.0),
            Component("VEE", "voltage_source", ["vee", "gnd"], value=-15.0),
            Component("VIN", "voltage_source", ["in", "gnd"], value=1.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        
        assert metrics.component_count == 7
        assert metrics.complexity_level in ["simple", "moderate"]
        assert metrics.active_components == 1  # opamp
        assert metrics.passive_components == 3  # R1, R2, C1
        assert metrics.power_components == 3   # VCC, VEE, VIN
    
    def test_complex_circuit_analysis(self):
        """Test analysis of a complex circuit."""
        # Create a complex circuit with many active components
        components = []
        
        # Add many different types of components
        for i in range(5):
            components.extend([
                Component(f"U{i}", "opamp", [f"in{i}", f"fb{i}", f"out{i}", "vcc", "vee"], gain=100000.0),
                Component(f"M{i}", "mosfet", [f"d{i}", f"g{i}", f"s{i}", "gnd"], model="NMOS"),
                Component(f"R{i}", "resistor", [f"out{i}", f"fb{i}"], value=10000.0),
                Component(f"C{i}", "capacitor", [f"out{i}", "gnd"], value=1e-9)
            ])
        
        # Add power supplies
        components.extend([
            Component("VCC", "voltage_source", ["vcc", "gnd"], value=15.0),
            Component("VEE", "voltage_source", ["vee", "gnd"], value=-15.0)
        ])
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        
        assert metrics.component_count == 22  # 5*4 + 2
        assert metrics.complexity_level in ["complex", "very_complex"]
        assert metrics.active_components == 10  # 5 opamps + 5 mosfets
        assert metrics.passive_components == 10  # 5 resistors + 5 capacitors
        assert metrics.power_components == 2   # VCC, VEE
    
    def test_empty_circuit_analysis(self):
        """Test analysis of empty circuit."""
        components = []
        metrics = self.analyzer.analyze_circuit_complexity(components)
        
        assert metrics.component_count == 0
        assert metrics.complexity_level == "simple"
        assert metrics.complexity_score == 0.0
    
    def test_datasheet_prompts_simple_circuit(self):
        """Test that simple circuits don't generate datasheet prompts."""
        components = [
            Component("R1", "resistor", ["n1", "n2"], value=1000.0),
            Component("R2", "resistor", ["n2", "gnd"], value=2000.0),
            Component("V1", "voltage_source", ["n1", "gnd"], value=5.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        prompts = self.analyzer.generate_datasheet_prompts(components, metrics)
        
        assert len(prompts) == 0
        assert not self.analyzer.should_prompt_for_datasheets(metrics)
    
    def test_datasheet_prompts_opamp_circuit(self):
        """Test datasheet prompts for circuits with op-amps."""
        components = [
            Component("U1", "opamp", ["in", "fb", "out", "vcc", "vee"], gain=100000.0),
            Component("R1", "resistor", ["out", "fb"], value=10000.0),
            Component("VCC", "voltage_source", ["vcc", "gnd"], value=15.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        prompts = self.analyzer.generate_datasheet_prompts(components, metrics)
        
        assert len(prompts) > 0
        assert any(p.component_type == "opamp" for p in prompts)
        assert any(p.priority in ["recommended", "critical"] for p in prompts)
    
    def test_datasheet_prompts_complex_circuit(self):
        """Test datasheet prompts for complex circuits."""
        components = [
            Component("U1", "opamp", ["in1", "fb1", "out1", "vcc", "vee"], gain=100000.0),
            Component("U2", "opamp", ["in2", "fb2", "out2", "vcc", "vee"], gain=100000.0),
            Component("M1", "mosfet", ["d1", "g1", "s1", "gnd"], model="NMOS"),
            Component("M2", "mosfet", ["d2", "g2", "s2", "gnd"], model="PMOS"),
            Component("ADC1", "adc", ["analog_in", "digital_out", "vcc", "gnd"], resolution=12),
            Component("DAC1", "dac", ["digital_in", "analog_out", "vcc", "gnd"], resolution=10)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        prompts = self.analyzer.generate_datasheet_prompts(components, metrics)
        
        assert len(prompts) >= 4  # opamp, mosfet, adc, dac
        assert self.analyzer.should_prompt_for_datasheets(metrics)
        
        # Check that we have critical prompts for complex circuit
        critical_prompts = [p for p in prompts if p.priority == "critical"]
        assert len(critical_prompts) > 0
    
    def test_datasheet_prompt_content(self):
        """Test the content of datasheet prompts."""
        components = [
            Component("U1", "opamp", ["in", "fb", "out", "vcc", "vee"], gain=100000.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        prompts = self.analyzer.generate_datasheet_prompts(components, metrics)
        
        assert len(prompts) == 1
        prompt = prompts[0]
        
        assert prompt.component_type == "opamp"
        assert prompt.priority in ["critical", "recommended", "optional"]
        assert len(prompt.suggested_parts) > 0
        assert "LM741" in prompt.suggested_parts or "LM358" in prompt.suggested_parts
        assert len(prompt.example_datasheets) > 0
        assert prompt.reason != ""
        assert prompt.impact != ""
    
    def test_component_needs_analysis(self):
        """Test the component needs analysis."""
        components = [
            Component("U1", "opamp", ["in", "fb", "out", "vcc", "vee"], gain=100000.0),
            Component("R1", "resistor", ["out", "fb"], value=10000.0)
        ]
        
        analysis = self.analyzer._analyze_component_needs(components)
        
        assert "opamp" in analysis
        assert "resistor" in analysis
        
        opamp_analysis = analysis["opamp"]
        assert opamp_analysis["count"] == 1
        assert opamp_analysis["needs_datasheet"] == True
        assert opamp_analysis["complexity_weight"] >= 3
        
        resistor_analysis = analysis["resistor"]
        assert resistor_analysis["count"] == 1
        assert resistor_analysis["needs_datasheet"] == False  # Simple component
    
    def test_circuit_analysis_report(self):
        """Test the comprehensive circuit analysis report."""
        components = [
            Component("U1", "opamp", ["in", "fb", "out", "vcc", "vee"], gain=100000.0),
            Component("M1", "mosfet", ["d", "g", "s", "gnd"], model="NMOS"),
            Component("R1", "resistor", ["out", "fb"], value=10000.0),
            Component("VCC", "voltage_source", ["vcc", "gnd"], value=15.0)
        ]
        
        report = self.analyzer.generate_circuit_analysis_report(components)
        
        # Check report structure
        assert "complexity_metrics" in report
        assert "datasheet_recommendations" in report
        assert "recommendations" in report
        
        # Check complexity metrics
        metrics = report["complexity_metrics"]
        assert metrics["component_count"] == 4
        assert metrics["level"] in ["simple", "moderate", "complex", "very_complex"]
        assert "breakdown" in metrics
        
        # Check datasheet recommendations
        ds_rec = report["datasheet_recommendations"]
        assert "should_prompt" in ds_rec
        assert "total_prompts" in ds_rec
        assert "prompts" in ds_rec
        
        # Check general recommendations
        assert isinstance(report["recommendations"], list)
    
    def test_priority_ordering(self):
        """Test that datasheet prompts are ordered by priority."""
        components = [
            Component("U1", "opamp", ["in1", "fb1", "out1", "vcc", "vee"], gain=100000.0),
            Component("M1", "mosfet", ["d1", "g1", "s1", "gnd"], model="NMOS"),
            Component("ADC1", "adc", ["ain", "dout", "vcc", "gnd"], resolution=12),
            Component("R1", "resistor", ["out1", "fb1"], value=10000.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        prompts = self.analyzer.generate_datasheet_prompts(components, metrics)
        
        # Check that prompts are ordered: critical, recommended, optional
        if len(prompts) > 1:
            for i in range(len(prompts) - 1):
                current_priority = prompts[i].priority
                next_priority = prompts[i + 1].priority
                
                priority_order = {"critical": 0, "recommended": 1, "optional": 2}
                assert priority_order[current_priority] <= priority_order[next_priority]
    
    def test_unknown_component_handling(self):
        """Test handling of unknown component types."""
        components = [
            Component("UNKNOWN1", "mystery_component", ["n1", "n2"], value=1.0),
            Component("UNKNOWN2", "exotic_device", ["n2", "n3"], param1=2.0)
        ]
        
        metrics = self.analyzer.analyze_circuit_complexity(components)
        prompts = self.analyzer.generate_datasheet_prompts(components, metrics)
        
        # Unknown components should be counted and may generate prompts
        assert metrics.unknown_components > 0
        
        # Should prompt for datasheets due to unknown components
        assert self.analyzer.should_prompt_for_datasheets(metrics)
    
    def test_complexity_thresholds(self):
        """Test that complexity thresholds work correctly."""
        # Test simple threshold
        simple_components = [Component(f"R{i}", "resistor", [f"n{i}", f"n{i+1}"], value=1000.0) 
                           for i in range(3)]
        simple_metrics = self.analyzer.analyze_circuit_complexity(simple_components)
        assert simple_metrics.complexity_level == "simple"
        
        # Test moderate threshold
        moderate_components = [Component(f"R{i}", "resistor", [f"n{i}", f"n{i+1}"], value=1000.0) 
                             for i in range(8)]
        moderate_metrics = self.analyzer.analyze_circuit_complexity(moderate_components)
        assert moderate_metrics.complexity_level in ["simple", "moderate"]
        
        # Test complex with high-weight components
        complex_components = [Component(f"U{i}", "opamp", [f"in{i}", f"fb{i}", f"out{i}", "vcc", "vee"], 
                                      gain=100000.0) for i in range(8)]
        complex_metrics = self.analyzer.analyze_circuit_complexity(complex_components)
        assert complex_metrics.complexity_level in ["complex", "very_complex"]


if __name__ == "__main__":
    pytest.main([__file__]) 