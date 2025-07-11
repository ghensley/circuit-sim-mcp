#!/usr/bin/env python3
"""
Debug PySpice integration to understand the naming issue.
"""

import sys
import os

# Set environment
os.environ['DYLD_LIBRARY_PATH'] = "/opt/homebrew/Cellar/libngspice/44.2/lib"

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PySpice.Spice.Netlist import Circuit as PySpiceCircuit
    from PySpice.Unit import *
    print("✅ PySpice imported successfully")
except ImportError as e:
    print(f"❌ PySpice import failed: {e}")
    sys.exit(1)

def test_direct_pyspice():
    """Test PySpice directly with manual circuit creation."""
    print("\n🔬 Testing PySpice directly...")
    
    try:
        # Create circuit
        circuit = PySpiceCircuit('test_voltage_divider')
        
        # Add components - test both naming styles
        print("Adding voltage source...")
        circuit.V('1', 'vcc', 'gnd', 5@u_V)  # Clean name
        
        print("Adding resistors...")
        circuit.R('1', 'vcc', 'output', 1000@u_Ω)  # Clean name
        circuit.R('2', 'output', 'gnd', 1000@u_Ω)   # Clean name
        
        print("Circuit components:")
        for element in circuit:
            print(f"  {element}")
        
        # Try simulation - use operating_point() instead of dc()
        print("Running simulation...")
        simulator = circuit.simulator(temperature=25, nominal_temperature=25)
        analysis = simulator.operating_point()  # Fixed: use operating_point() instead of dc()
        
        output_voltage = float(analysis['output'])
        print(f"✅ PySpice simulation successful!")
        print(f"Output voltage: {output_voltage:.2f}V")
        return True
        
    except Exception as e:
        print(f"❌ PySpice simulation failed: {e}")
        return False

def test_with_bad_names():
    """Test PySpice with problematic names."""
    print("\n🔬 Testing PySpice with component names like 'V1'...")
    
    try:
        # Create circuit
        circuit = PySpiceCircuit('test_bad_names')
        
        # Add components with names that include SPICE prefixes
        print("Adding voltage source with name 'V1'...")
        circuit.V('V1', 'vcc', 'gnd', 5@u_V)  # This might cause issues
        
        print("Adding resistors with names 'R1', 'R2'...")
        circuit.R('R1', 'vcc', 'output', 1000@u_Ω)
        circuit.R('R2', 'output', 'gnd', 1000@u_Ω)
        
        print("Circuit components:")
        for element in circuit:
            print(f"  {element}")
        
        # Try simulation - use operating_point() instead of dc()
        print("Running simulation...")
        simulator = circuit.simulator(temperature=25, nominal_temperature=25)
        analysis = simulator.operating_point()  # Fixed: use operating_point() instead of dc()
        
        output_voltage = float(analysis['output'])
        print(f"✅ PySpice simulation with bad names successful!")
        print(f"Output voltage: {output_voltage:.2f}V")
        return True
        
    except Exception as e:
        print(f"❌ PySpice simulation with bad names failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 PySpice Debug Session")
    print("=" * 40)
    
    success1 = test_direct_pyspice()
    success2 = test_with_bad_names()
    
    print("\n" + "=" * 40)
    print("📊 Debug Results")
    print("=" * 40)
    
    if success1:
        print("✅ Direct PySpice works")
    else:
        print("❌ Direct PySpice failed")
    
    if success2:
        print("✅ PySpice works with SPICE-prefixed names")
    else:
        print("❌ PySpice fails with SPICE-prefixed names")
    
    if success1 and success2:
        print("\n💡 Conclusion: Both direct PySpice and component naming work!")
        print("   🎉 All PySpice integration issues resolved!")
    elif success1 and not success2:
        print("\n💡 Conclusion: Component naming is the issue!")
        print("   Solution: Strip SPICE prefixes from component names before passing to PySpice")
    else:
        print("\n💡 Conclusion: PySpice has broader issues")
        print("   May be related to ngspice version compatibility") 