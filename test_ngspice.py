#!/usr/bin/env python3
"""
Test ngspice connectivity and actual circuit simulation.
This test validates that ngspice is properly installed and can execute simulations.
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_sim_mcp.circuit import Circuit, Component
from circuit_sim_mcp.simulator import CircuitSimulator


def check_ngspice_installation():
    """Check if ngspice is installed and accessible."""
    print("🔍 Checking ngspice installation...")
    
    # Check if ngspice is in PATH
    try:
        result = subprocess.run(['ngspice', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_info = result.stdout.strip()
            print(f"   ✅ ngspice found in PATH: {version_info.split()[0]} {version_info.split()[1]}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # Check Homebrew installation
    homebrew_paths = [
        "/opt/homebrew/bin/ngspice",
        "/usr/local/bin/ngspice"
    ]
    
    for path in homebrew_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                    print(f"   ✅ ngspice found at {path}: {version_info.split()[0]} {version_info.split()[1]}")
                    return True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    print("   ❌ ngspice not found")
    print("   💡 Install with: brew install ngspice")
    return False


def check_environment_variables():
    """Check if required environment variables are set."""
    print("\n🌍 Checking environment variables...")
    
    dyld_path = os.environ.get('DYLD_LIBRARY_PATH')
    if dyld_path:
        print(f"   ✅ DYLD_LIBRARY_PATH set: {dyld_path}")
        
        # Check if the path actually exists
        for path in dyld_path.split(':'):
            if 'ngspice' in path or 'libngspice' in path:
                if os.path.exists(path):
                    print(f"   ✅ ngspice library path exists: {path}")
                    return True
                else:
                    print(f"   ⚠️  ngspice library path doesn't exist: {path}")
    else:
        print("   ⚠️  DYLD_LIBRARY_PATH not set")
        
        # Try to find libngspice automatically
        potential_paths = [
            "/opt/homebrew/Cellar/libngspice/44.2/lib",
            "/opt/homebrew/lib",
            "/usr/local/lib"
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                lib_files = [f for f in os.listdir(path) if 'ngspice' in f.lower()]
                if lib_files:
                    print(f"   💡 Found ngspice libraries at: {path}")
                    print(f"   💡 Set environment: export DYLD_LIBRARY_PATH=\"{path}\"")
                    return False
        
        print("   ❌ No ngspice libraries found")
    
    return False


def test_simple_netlist():
    """Test ngspice with a simple netlist file."""
    print("\n📄 Testing simple SPICE netlist...")
    
    # Create a simple voltage divider netlist
    netlist = """Simple Voltage Divider Test
* Generated for ngspice connectivity test
V1 vcc gnd 5.0
R1 vcc output 1000.0
R2 output gnd 1000.0

.dc V1 5 5 1
.print dc v(output)
.end
"""
    
    # Write to temporary file
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cir', delete=False) as f:
            f.write(netlist)
            netlist_file = f.name
        
        # Try to run ngspice with the netlist
        try:
            # Set environment for this test
            env = os.environ.copy()
            if not env.get('DYLD_LIBRARY_PATH'):
                # Try common paths
                for path in ["/opt/homebrew/Cellar/libngspice/44.2/lib", "/opt/homebrew/lib"]:
                    if os.path.exists(path):
                        env['DYLD_LIBRARY_PATH'] = path
                        break
            
            result = subprocess.run([
                'ngspice', '-b', '-r', '/dev/null', netlist_file
            ], capture_output=True, text=True, timeout=10, env=env)
            
            if result.returncode == 0:
                print("   ✅ ngspice successfully executed netlist")
                # Look for voltage output in the result
                if "v(output)" in result.stdout.lower() or "2.5" in result.stdout:
                    print("   ✅ Simulation produced expected results")
                return True
            else:
                print("   ❌ ngspice execution failed")
                print(f"   Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ❌ ngspice execution timed out")
            return False
        except FileNotFoundError:
            print("   ❌ ngspice command not found")
            return False
        finally:
            # Clean up
            if os.path.exists(netlist_file):
                os.unlink(netlist_file)
                
    except Exception as e:
        print(f"   ❌ Failed to create test netlist: {e}")
        return False


def test_pyspice_integration():
    """Test PySpice integration with ngspice."""
    print("\n🐍 Testing PySpice integration...")
    
    try:
        # Set environment variable if needed
        if not os.environ.get('DYLD_LIBRARY_PATH'):
            for path in ["/opt/homebrew/Cellar/libngspice/44.2/lib", "/opt/homebrew/lib"]:
                if os.path.exists(path):
                    os.environ['DYLD_LIBRARY_PATH'] = path
                    print(f"   🔧 Set DYLD_LIBRARY_PATH to {path}")
                    break
        
        # Import PySpice directly and create a simple circuit
        from PySpice.Spice.Netlist import Circuit as PySpiceCircuit
        from PySpice.Unit import u_V, u_Ohm
        
        # Create a simple voltage divider circuit
        circuit = PySpiceCircuit('pyspice_test')
        circuit.V('supply', 'vcc', circuit.gnd, 5@u_V)
        circuit.R(1, 'vcc', 'output', 1000@u_Ohm) 
        circuit.R(2, 'output', circuit.gnd, 1000@u_Ohm)
        
        # Run operating point analysis (this works reliably)
        simulator = circuit.simulator(temperature=25, nominal_temperature=25)
        analysis = simulator.operating_point()
        
        # Check results
        output_voltage = float(analysis['output'])
        
        if 2.0 <= output_voltage <= 3.0:
            print(f"   ✅ PySpice simulation successful: output = {output_voltage:.3f}V")
            return True
        else:
            print(f"   ⚠️  PySpice simulation unexpected result: output = {output_voltage}V")
            return False
            
    except Exception as e:
        error_str = str(e)
        
        # Check for specific PySpice/ngspice compatibility issues
        if "Unsupported Ngspice version" in error_str:
            print(f"   ❌ PySpice version incompatibility: {e}")
            print("   💡 Known issue: PySpice doesn't officially support ngspice 44 yet")
            print("   💡 Solutions:")
            print("      1. Use direct ngspice calls (which work fine)")
            print("      2. Wait for PySpice update")
            print("      3. Consider downgrading to ngspice 42 for PySpice compatibility")
        elif "voltage source, current source, or resistor named \"\"" in error_str:
            print(f"   ❌ PySpice internal naming issue: {e}")
            print("   💡 This appears to be a PySpice/ngspice 44 compatibility bug")
        else:
            print(f"   ❌ PySpice simulation failed: {e}")
            
            # Provide specific guidance based on error type
            error_str_lower = error_str.lower()
            if "ngspice not found" in error_str_lower:
                print("   💡 Solution: Install ngspice with 'brew install ngspice'")
            elif "library" in error_str_lower or "dyld" in error_str_lower:
                print("   💡 Solution: Set DYLD_LIBRARY_PATH to ngspice lib directory")
            elif "import" in error_str_lower:
                print("   💡 Solution: Install PySpice with 'pip install PySpice'")
        
        return False


def provide_setup_guidance():
    """Provide setup guidance for ngspice."""
    print("\n📋 ngspice Setup Guidance")
    print("=" * 40)
    print("1. Install ngspice:")
    print("   brew install ngspice")
    print("")
    print("2. Set environment variable (for shell):")
    print("   export DYLD_LIBRARY_PATH=\"/opt/homebrew/Cellar/libngspice/44.2/lib\"")
    print("")
    print("3. For MCP integration, add to mcp-config.json:")
    print('   "env": {')
    print('     "DYLD_LIBRARY_PATH": "/opt/homebrew/Cellar/libngspice/44.2/lib"')
    print('   }')
    print("")
    print("4. Verify installation:")
    print("   python3 test_ngspice.py")


def main():
    """Run ngspice connectivity tests."""
    print("🧪 ngspice Connectivity Test Suite")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # Test 1: Check ngspice installation
    if check_ngspice_installation():
        success_count += 1
    
    # Test 2: Check environment variables
    if check_environment_variables():
        success_count += 1
    
    # Test 3: Test simple netlist
    if test_simple_netlist():
        success_count += 1
    
    # Test 4: Test PySpice integration
    if test_pyspice_integration():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 ngspice Test Summary")
    print("=" * 50)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All ngspice tests passed!")
        print("✨ Circuit simulation is fully functional")
        return True
    elif success_count == 0:
        print("🚨 All ngspice tests failed")
        provide_setup_guidance()
        return False
    else:
        print("⚠️  Some ngspice tests failed")
        if success_count < 2:
            provide_setup_guidance()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 