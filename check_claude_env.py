#!/usr/bin/env python3
"""
Environment check script for Claude Desktop debugging.
Run this to check environment variables and library paths.
"""

import os
import sys

def check_environment():
    print("🔍 Claude Desktop Environment Check")
    print("=" * 40)
    
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    
    print("\n📁 Python path:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    
    print(f"\n🌍 Environment variables:")
    env_vars = ['DYLD_LIBRARY_PATH', 'PATH', 'PYTHONPATH']
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        if len(value) > 100:
            value = value[:100] + "..."
        print(f"  {var}: {value}")
    
    print(f"\n📦 Package checks:")
    try:
        import PySpice
        print(f"  ✅ PySpice: {PySpice.__version__} at {PySpice.__file__}")
    except Exception as e:
        print(f"  ❌ PySpice: {e}")
    
    try:
        from PySpice.Spice.NgSpice import SimulationType
        print(f"  ✅ SimulationType LAST_VERSION: {SimulationType.LAST_VERSION}")
    except Exception as e:
        print(f"  ❌ SimulationType: {e}")
    
    try:
        from PySpice.Spice.NgSpice.Shared import NgSpiceShared
        ngspice = NgSpiceShared.new_instance()
        print(f"  ✅ NgSpice shared library: loaded successfully")
    except Exception as e:
        print(f"  ❌ NgSpice shared library: {e}")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    check_environment() 