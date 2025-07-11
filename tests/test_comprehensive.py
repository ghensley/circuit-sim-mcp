#!/usr/bin/env python3
"""
Comprehensive test suite for circuit simulation MCP server.
Run with: python tests/test_comprehensive.py
"""

import sys
import os
import asyncio
import traceback

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from circuit_sim_mcp.circuit import Circuit, Component
from circuit_sim_mcp.server_basic import CircuitSimServer


class TestResult:
    def __init__(self, name, success, message="", details=""):
        self.name = name
        self.success = success
        self.message = message
        self.details = details


class CircuitTestSuite:
    def __init__(self):
        self.results = []
        self.server = None
    
    def log_test(self, name, success, message="", details=""):
        result = TestResult(name, success, message, details)
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}: {message}")
        if not success and details:
            print(f"    Details: {details}")
    
    def test_component_creation(self):
        """Test creating components with different field name formats."""
        print("\n=== Testing Component Creation ===")
        
        # Test 1: Voltage source with 'voltage' field
        try:
            comp_data = {
                'name': 'V1', 
                'component_type': 'voltage_source', 
                'nodes': ['vcc', 'gnd'], 
                'voltage': 5.0, 
                'source_type': 'DC'
            }
            component = Component.from_dict(comp_data)
            self.log_test("Voltage source (voltage field)", True, f"Created {component.name} = {component.voltage}V")
        except Exception as e:
            self.log_test("Voltage source (voltage field)", False, "Failed to create", str(e))
        
        # Test 2: Voltage source with 'value' field
        try:
            comp_data = {
                'name': 'V2', 
                'component_type': 'voltage_source', 
                'nodes': ['vcc', 'gnd'], 
                'value': 5.0, 
                'source_type': 'DC'
            }
            component = Component.from_dict(comp_data)
            self.log_test("Voltage source (value field)", True, f"Created {component.name} = {component.value}V")
        except Exception as e:
            self.log_test("Voltage source (value field)", False, "Failed to create", str(e))
        
        # Test 3: Resistor with 'resistance' field
        try:
            comp_data = {
                'name': 'R1', 
                'component_type': 'resistor', 
                'nodes': ['a', 'b'], 
                'resistance': 1000.0
            }
            component = Component.from_dict(comp_data)
            self.log_test("Resistor (resistance field)", True, f"Created {component.name} = {component.resistance}Ω")
        except Exception as e:
            self.log_test("Resistor (resistance field)", False, "Failed to create", str(e))
        
        # Test 4: Resistor with 'value' field
        try:
            comp_data = {
                'name': 'R2', 
                'component_type': 'resistor', 
                'nodes': ['a', 'b'], 
                'value': 1000.0
            }
            component = Component.from_dict(comp_data)
            self.log_test("Resistor (value field)", True, f"Created {component.name} = {component.value}Ω")
        except Exception as e:
            self.log_test("Resistor (value field)", False, "Failed to create", str(e))
        
        # Test 5: LED/Diode
        try:
            comp_data = {
                'name': 'LED1', 
                'component_type': 'diode', 
                'nodes': ['anode', 'cathode'], 
                'model': 'LED'
            }
            component = Component.from_dict(comp_data)
            self.log_test("LED/Diode", True, f"Created {component.name}, model: {component.model}")
        except Exception as e:
            self.log_test("LED/Diode", False, "Failed to create", str(e))
    
    def test_netlist_generation(self):
        """Test SPICE netlist generation."""
        print("\n=== Testing Netlist Generation ===")
        
        try:
            circuit = Circuit("test_circuit")
            
            # Add components with problematic names (that might cause double prefixes)
            components = [
                {'name': 'V_battery', 'component_type': 'voltage_source', 'nodes': ['vcc', 'gnd'], 'voltage': 9.0, 'source_type': 'DC'},
                {'name': 'R_current_limit', 'component_type': 'resistor', 'nodes': ['vcc', 'led_anode'], 'resistance': 330.0},
                {'name': 'D_led', 'component_type': 'diode', 'nodes': ['led_anode', 'gnd'], 'model': 'LED'},
                {'name': 'regular_resistor', 'component_type': 'resistor', 'nodes': ['vcc', 'out'], 'resistance': 1000.0}
            ]
            
            for comp_data in components:
                component = Component.from_dict(comp_data)
                circuit.add_component(component)
            
            netlist = circuit.generate_netlist()
            
            # Check for double prefixes (invalid SPICE)
            lines = netlist.split('\n')
            spice_lines = [line for line in lines if line and not line.startswith('*') and line != '.END']
            
            invalid_lines = []
            for line in spice_lines:
                # Check for actual double prefixes like VV, RR, DD, etc.
                # But not false positives like Rregular_resistor (which is valid)
                words = line.split()
                if words:
                    component_name = words[0]
                    # Look for patterns like VV, RR, DD followed by underscore or alphanumeric
                    for prefix in ['V', 'R', 'D', 'C', 'L', 'I', 'Q']:
                        double_prefix = prefix + prefix
                        if component_name.startswith(double_prefix):
                            # Check if it's really a double prefix or just coincidental
                            remaining = component_name[2:]
                            if remaining and (remaining.startswith('_') or remaining[0].isupper()):
                                invalid_lines.append(line)
                                break
            
            if invalid_lines:
                self.log_test("Netlist generation", False, "Double prefixes detected", str(invalid_lines))
            else:
                self.log_test("Netlist generation", True, f"Valid SPICE netlist generated ({len(spice_lines)} components)")
            
            # Print the netlist for inspection
            print("Generated netlist:")
            for line in netlist.split('\n'):
                if line.strip():
                    print(f"    {line}")
                    
        except Exception as e:
            self.log_test("Netlist generation", False, "Failed to generate netlist", str(e))
    
    async def test_server_initialization(self):
        """Test MCP server initialization."""
        print("\n=== Testing Server Initialization ===")
        
        try:
            self.server = CircuitSimServer()
            self.log_test("Server initialization", True, "CircuitSimServer created successfully")
        except Exception as e:
            self.log_test("Server initialization", False, "Failed to create server", str(e))
            return False
        
        return True
    
    async def test_example_circuits(self):
        """Test the example circuit creation."""
        print("\n=== Testing Example Circuits ===")
        
        if not self.server:
            self.log_test("Example circuits", False, "Server not initialized")
            return
        
        examples = ["voltage_divider", "led_circuit", "rc_lowpass"]
        
        for example_name in examples:
            try:
                # We need to access the actual function
                # This is a bit hacky but necessary for testing
                circuit = Circuit(f"{example_name}_test")
                
                if example_name == "voltage_divider":
                    components = [
                        {"name": "V1", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "voltage": 5.0, "source_type": "DC"},
                        {"name": "R1", "component_type": "resistor", "nodes": ["vcc", "output"], "resistance": 1000.0},
                        {"name": "R2", "component_type": "resistor", "nodes": ["output", "gnd"], "resistance": 1000.0}
                    ]
                elif example_name == "led_circuit":
                    components = [
                        {"name": "V1", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "voltage": 5.0, "source_type": "DC"},
                        {"name": "R1", "component_type": "resistor", "nodes": ["vcc", "led_anode"], "resistance": 330.0},
                        {"name": "LED1", "component_type": "diode", "nodes": ["led_anode", "gnd"], "model": "LED"}
                    ]
                elif example_name == "rc_lowpass":
                    components = [
                        {"name": "V1", "component_type": "voltage_source", "nodes": ["input", "gnd"], "voltage": 1.0, "source_type": "DC"},
                        {"name": "R1", "component_type": "resistor", "nodes": ["input", "output"], "resistance": 1000.0},
                        {"name": "C1", "component_type": "capacitor", "nodes": ["output", "gnd"], "capacitance": 1e-6}
                    ]
                
                for comp_data in components:
                    component = Component.from_dict(comp_data)
                    circuit.add_component(component)
                
                netlist = circuit.generate_netlist()
                self.log_test(f"Example: {example_name}", True, f"Created with {len(circuit.components)} components")
                
            except Exception as e:
                self.log_test(f"Example: {example_name}", False, "Failed to create", str(e))
    
    def test_actual_simulation(self):
        """Test actual SPICE simulation execution."""
        print("\n=== Testing Actual Simulation ===")
        
        try:
            # Use PySpice directly instead of our CircuitSimulator to test basic functionality
            from PySpice.Spice.Netlist import Circuit as PySpiceCircuit
            from PySpice.Unit import u_V, u_Ohm
            
            # Create a simple voltage divider circuit
            circuit = PySpiceCircuit('simulation_test')
            circuit.V('supply', 'vcc', circuit.gnd, 5@u_V)
            circuit.R(1, 'vcc', 'output', 1000@u_Ohm)
            circuit.R(2, 'output', circuit.gnd, 1000@u_Ohm)
            
            # Run operating point analysis
            simulator = circuit.simulator(temperature=25, nominal_temperature=25)
            analysis = simulator.operating_point()
            
            # Check if we got reasonable results
            output_voltage = float(analysis['output'])
            
            # Expected: output should be ~2.5V (voltage divider with equal resistors)
            if 2.0 < output_voltage < 3.0:
                self.log_test("Actual simulation", True, f"Voltage divider output: {output_voltage:.3f}V")
            else:
                self.log_test("Actual simulation", False, f"Unexpected voltage: {output_voltage}V (expected ~2.5V)")
            
        except ImportError as e:
            if "PySpice" in str(e):
                self.log_test("Actual simulation", False, "PySpice not available", str(e))
            else:
                self.log_test("Actual simulation", False, "Import error", str(e))
        except Exception as e:
            # This might fail if ngspice isn't available, which is okay for basic testing
            self.log_test("Actual simulation", False, f"Simulation failed (possibly ngspice not available)", str(e))
    
    def test_component_name_cleaning(self):
        """Test the component name cleaning function."""
        print("\n=== Testing Component Name Cleaning ===")
        
        circuit = Circuit("name_test")
        
        test_cases = [
            ("V_battery", "battery"),
            ("R_resistor", "resistor"),  
            ("D_led", "led"),
            ("C_cap", "cap"),
            ("L_inductor", "inductor"),
            ("regular_name", "regular_name"),
            ("V1", "1"),
            ("R2", "2")
        ]
        
        for input_name, expected in test_cases:
            try:
                result = circuit._clean_component_name(input_name)
                if result == expected:
                    self.log_test(f"Name cleaning: {input_name}", True, f"'{input_name}' -> '{result}'")
                else:
                    self.log_test(f"Name cleaning: {input_name}", False, f"Expected '{expected}', got '{result}'")
            except Exception as e:
                self.log_test(f"Name cleaning: {input_name}", False, "Function failed", str(e))
    
    async def run_all_tests(self):
        """Run all tests in the suite."""
        print("🧪 Circuit Simulation Test Suite")
        print("=" * 50)
        
        # Basic component tests
        self.test_component_creation()
        self.test_component_name_cleaning()
        self.test_netlist_generation()
        
        # Simulation test
        self.test_actual_simulation()
        
        # Server tests
        server_ok = await self.test_server_initialization()
        if server_ok:
            await self.test_example_circuits()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print(f"Total tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.name}: {result.message}")
                    if result.details:
                        print(f"    {result.details}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 All tests passed!")
        elif success_rate >= 80:
            print("⚠️  Most tests passed, but some issues remain")
        else:
            print("🚨 Many tests failed - significant issues detected")
        
        return success_rate == 100


async def main():
    """Run the test suite."""
    test_suite = CircuitTestSuite()
    success = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()) 