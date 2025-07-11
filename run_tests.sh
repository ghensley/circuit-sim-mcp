#!/bin/bash

echo "🧪 Circuit Simulation MCP - Test Runner"
echo "======================================="

# Set up proper environment for ARM64 ngspice
export PATH="/opt/homebrew/bin:$PATH"
export DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/libngspice/44.2/lib:$DYLD_LIBRARY_PATH"

# Check if we're in the right directory
if [ ! -f "circuit_sim_mcp/circuit.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Make sure we have python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not found"
    exit 1
fi

# Parse command line arguments
TEST_TYPE="all"
if [ $# -gt 0 ]; then
    TEST_TYPE="$1"
fi

case $TEST_TYPE in
    "quick")
        echo "🏃‍♂️ Running quick tests..."
        echo ""
        python3 quick_test.py
        exit $?
        ;;
    "ngspice")
        echo "🔌 Running ngspice connectivity tests..."
        echo ""
        python3 test_ngspice.py
        exit $?
        ;;
    "comprehensive")
        echo "🏃 Running comprehensive test suite..."
        echo ""
        python3 tests/test_comprehensive.py
        exit $?
        ;;
    "all")
        echo "🏃 Running all test suites..."
        echo ""
        
        # Run quick tests first
        echo "1️⃣ Quick Tests:"
        python3 quick_test.py
        quick_result=$?
        
        echo ""
        echo "2️⃣ ngspice Connectivity:"
        python3 test_ngspice.py
        ngspice_result=$?
        
        echo ""
        echo "3️⃣ Comprehensive Tests:"
        python3 tests/test_comprehensive.py
        comprehensive_result=$?
        
        # Summary
        echo ""
        echo "======================================="
        echo "📊 All Tests Summary"
        echo "======================================="
        
        if [ $quick_result -eq 0 ]; then
            echo "✅ Quick tests: PASSED"
        else
            echo "❌ Quick tests: FAILED"
        fi
        
        if [ $ngspice_result -eq 0 ]; then
            echo "✅ ngspice tests: PASSED"
        else
            echo "❌ ngspice tests: FAILED"
        fi
        
        if [ $comprehensive_result -eq 0 ]; then
            echo "✅ Comprehensive tests: PASSED"
        else
            echo "❌ Comprehensive tests: FAILED"
        fi
        
        # Overall result
        if [ $quick_result -eq 0 ] && [ $ngspice_result -eq 0 ] && [ $comprehensive_result -eq 0 ]; then
            echo ""
            echo "🎉 ALL TESTS PASSED! Circuit simulation is fully functional."
            exit 0
        else
            echo ""
            echo "⚠️  Some tests failed. Check individual results above."
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 [quick|ngspice|comprehensive|all]"
        echo ""
        echo "Test types:"
        echo "  quick        - Fast basic functionality tests"
        echo "  ngspice      - ngspice connectivity and simulation tests"
        echo "  comprehensive - Full test suite (excludes ngspice)"
        echo "  all          - Run all test suites (default)"
        exit 1
        ;;
esac 