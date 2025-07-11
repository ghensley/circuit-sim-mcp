#!/usr/bin/env python3
"""
Quick test for basic circuit simulation functionality.
This test validates component creation and netlist generation without requiring ngspice.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_sim_mcp.circuit import Circuit, Component


def test_basic_functionality():
    """Test basic circuit functionality."""
    print("🔬 Quick Circuit Simulation Test")
    print("=" * 40)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Component creation with different field formats
    print("\n1. Testing component creation...")
    try:
        # Test voltage source with both formats
        v1 = Component.from_dict({
            'name': 'V1', 
            'component_type': 'voltage_source', 
            'nodes': ['vcc', 'gnd'], 
            'voltage': 5.0, 
            'source_type': 'DC'
        })
        
        v2 = Component.from_dict({
            'name': 'V2', 
            'component_type': 'voltage_source', 
            'nodes': ['vcc', 'gnd'], 
            'value': 5.0, 
            'source_type': 'DC'
        })
        
        # Test resistor with both formats
        r1 = Component.from_dict({
            'name': 'R1', 
            'component_type': 'resistor', 
            'nodes': ['a', 'b'], 
            'resistance': 1000.0
        })
        
        r2 = Component.from_dict({
            'name': 'R2', 
            'component_type': 'resistor', 
            'nodes': ['a', 'b'], 
            'value': 1000.0
        })
        
        print("   ✅ All component formats working")
        success_count += 1
    except Exception as e:
        print(f"   ❌ Component creation failed: {e}")
    total_tests += 1
    
    # Test 2: Circuit creation and netlist generation
    print("\n2. Testing circuit creation...")
    try:
        circuit = Circuit("quick_test")
        
        # Create a simple LED circuit
        components = [
            {"name": "V_battery", "component_type": "voltage_source", "nodes": ["vcc", "gnd"], "voltage": 5.0, "source_type": "DC"},
            {"name": "R_limit", "component_type": "resistor", "nodes": ["vcc", "led_anode"], "resistance": 330.0},
            {"name": "LED1", "component_type": "diode", "nodes": ["led_anode", "gnd"], "model": "LED"}
        ]
        
        for comp_data in components:
            component = Component.from_dict(comp_data)
            circuit.add_component(component)
        
        netlist = circuit.generate_netlist()
        
        # Basic validation
        if "Vbattery vcc gnd 5.0" in netlist and "Rlimit vcc led_anode 330.0" in netlist and "DLED1 led_anode gnd LED" in netlist:
            print("   ✅ Circuit creation and netlist generation working")
            success_count += 1
        else:
            print("   ❌ Netlist format incorrect")
            print("Generated netlist:")
            for line in netlist.split('\n'):
                if line.strip():
                    print(f"      {line}")
    except Exception as e:
        print(f"   ❌ Circuit creation failed: {e}")
    total_tests += 1
    
    # Test 3: Server import
    print("\n3. Testing server import...")
    try:
        from circuit_sim_mcp.server_basic import CircuitSimServer
        server = CircuitSimServer()
        print("   ✅ Server imports and initializes correctly")
        success_count += 1
    except Exception as e:
        print(f"   ❌ Server import failed: {e}")
    total_tests += 1
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Quick Test Summary")
    print("=" * 40)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All basic functionality working!")
        print("✨ Ready for MCP integration")
        return True
    else:
        print("⚠️  Some issues detected")
        print("🔧 Run './run_tests.sh' for detailed diagnostics")
        return False


if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1) 