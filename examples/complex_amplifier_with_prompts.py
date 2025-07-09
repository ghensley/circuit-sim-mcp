"""
Example: Complex Multi-Stage Amplifier with Intelligent Datasheet Prompting

This example demonstrates how the MCP server intelligently analyzes circuit complexity
and prompts users to upload relevant datasheets for optimal simulation accuracy.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from circuit_sim_mcp.circuit_analyzer import CircuitComplexityAnalyzer
from circuit_sim_mcp.circuit import Component


def demo_intelligent_datasheet_prompting():
    """Demonstrate intelligent datasheet prompting for complex circuits."""
    
    # Initialize the analyzer directly for demonstration
    analyzer = CircuitComplexityAnalyzer()
    
    print("🔬 Circuit Simulation MCP Server - Intelligent Datasheet Prompting Demo")
    print("=" * 80)
    
    # Example 1: Simple Circuit (no prompts expected)
    print("\n📋 Example 1: Simple Voltage Divider (Should NOT trigger prompts)")
    print("-" * 60)
    
    simple_components = [
        Component(name="V1", component_type="voltage_source", nodes=["vin", "gnd"], value=12.0),
        Component(name="R1", component_type="resistor", nodes=["vin", "vout"], value=10000.0),
        Component(name="R2", component_type="resistor", nodes=["vout", "gnd"], value=5000.0)
    ]
    
    metrics = analyzer.analyze_circuit_complexity(simple_components)
    report = analyzer.generate_circuit_analysis_report(simple_components)
    
    print(f"✅ Circuit analyzed: Simple voltage divider")
    print(f"📊 Complexity Level: {metrics.complexity_level}")
    print(f"🎯 Datasheet Prompts Needed: {report['datasheet_recommendations']['should_prompt']}")
    
    
    # Example 2: Moderately Complex Circuit (some prompts expected)
    print("\n📋 Example 2: Op-Amp Buffer Circuit (Should trigger RECOMMENDED prompts)")
    print("-" * 70)
    
    opamp_components = [
        Component(name="V1", component_type="voltage_source", nodes=["vin", "gnd"], value=5.0),
        Component(name="VCC", component_type="voltage_source", nodes=["vcc", "gnd"], value=15.0),
        Component(name="VEE", component_type="voltage_source", nodes=["vee", "gnd"], value=-15.0),
        Component(name="U1", component_type="opamp", nodes=["vin", "vout", "vout", "vcc", "vee"], value=100000.0),
        Component(name="RL", component_type="resistor", nodes=["vout", "gnd"], value=10000.0)
    ]
    
    metrics = analyzer.analyze_circuit_complexity(opamp_components)
    report = analyzer.generate_circuit_analysis_report(opamp_components)
    
    print(f"✅ Circuit analyzed: Op-amp buffer")
    print(f"📊 Complexity Level: {metrics.complexity_level}")
    print(f"🎯 Should Prompt for Datasheets: {report['datasheet_recommendations']['should_prompt']}")
    print(f"📈 Total Prompts: {report['datasheet_recommendations']['total_prompts']}")
    
    if report['datasheet_recommendations']['prompts']:
        print("\n📢 Datasheet Upload Prompts:")
        for prompt in report['datasheet_recommendations']['prompts']:
            print(f"   🔹 {prompt['priority'].upper()}: {prompt['component_type']}")
            print(f"      Reason: {prompt['reason']}")
            print(f"      Suggested Parts: {', '.join(prompt['suggested_parts'][:3])}")
            print()
    
    
    # Example 3: Very Complex Circuit (critical prompts expected)
    print("\n📋 Example 3: Complex Multi-Stage Amplifier (Should trigger CRITICAL prompts)")
    print("-" * 75)
    
    complex_components = [
        # Input stage with differential pair
        Component(name="VIN_P", component_type="voltage_source", nodes=["inp", "gnd"], value=0.001),
        Component(name="VIN_N", component_type="voltage_source", nodes=["inn", "gnd"], value=0.0),
        
        # Power supplies
        Component(name="VCC", component_type="voltage_source", nodes=["vcc", "gnd"], value=15.0),
        Component(name="VEE", component_type="voltage_source", nodes=["vee", "gnd"], value=-15.0),
        
        # First stage: Differential amplifier with MOSFETs
        Component(name="M1", component_type="mosfet", nodes=["drain1", "inp", "source_common", "gnd"]),
        Component(name="M2", component_type="mosfet", nodes=["drain2", "inn", "source_common", "gnd"]),
        Component(name="I_TAIL", component_type="current_source", nodes=["source_common", "vee"], value=0.001),
        
        # Active load (current mirror)
        Component(name="M3", component_type="mosfet", nodes=["vcc", "drain1", "drain1", "gnd"]),
        Component(name="M4", component_type="mosfet", nodes=["vcc", "drain1", "drain2", "gnd"]),
        
        # Second stage: Op-amp voltage amplifier
        Component(name="U1", component_type="opamp", nodes=["drain2", "fb_node", "amp_out", "vcc", "vee"], value=100000.0),
        
        # Feedback network
        Component(name="RF", component_type="resistor", nodes=["amp_out", "fb_node"], value=100000.0),
        Component(name="RG", component_type="resistor", nodes=["fb_node", "gnd"], value=10000.0),
        
        # Output stage: MOSFET power amplifier  
        Component(name="M5", component_type="mosfet", nodes=["vcc", "amp_out", "output", "gnd"]),
        Component(name="M6", component_type="mosfet", nodes=["output", "amp_out_inv", "vee", "gnd"]),
        
        # Inverter for complementary output stage
        Component(name="U2", component_type="opamp", nodes=["gnd", "amp_out", "amp_out_inv", "vcc", "vee"], value=-1.0),
        
        # Output load and filtering
        Component(name="RL", component_type="resistor", nodes=["output", "gnd"], value=8.0),
        Component(name="CL", component_type="capacitor", nodes=["output", "gnd"], value=100e-12),
        
        # Input filtering
        Component(name="RIN", component_type="resistor", nodes=["inp", "input_filtered"], value=1000.0),
        Component(name="CIN", component_type="capacitor", nodes=["input_filtered", "gnd"], value=1e-9),
        
        # Power supply decoupling
        Component(name="CVCC", component_type="capacitor", nodes=["vcc", "gnd"], value=100e-6),
        Component(name="CVEE", component_type="capacitor", nodes=["vee", "gnd"], value=100e-6),
        
        # Additional active components that need datasheets
        Component(name="ADC1", component_type="adc", nodes=["output", "digital_out", "vcc", "gnd"]),
        Component(name="DAC1", component_type="dac", nodes=["digital_in", "dac_out", "vcc", "gnd"]),
        Component(name="REG1", component_type="voltage_regulator", nodes=["vcc", "vreg", "gnd"])
    ]
    
    metrics = analyzer.analyze_circuit_complexity(complex_components)
    report = analyzer.generate_circuit_analysis_report(complex_components)
    
    print(f"✅ Circuit analyzed: Complex multi-stage amplifier")
    print(f"📊 Complexity Level: {metrics.complexity_level.upper()}")
    print(f"🎯 Should Prompt for Datasheets: {report['datasheet_recommendations']['should_prompt']}")
    print(f"📈 Total Prompts: {report['datasheet_recommendations']['total_prompts']}")
    print(f"🚨 Critical Prompts: {report['datasheet_recommendations']['critical_prompts']}")
    print(f"⚠️  Recommended Prompts: {report['datasheet_recommendations']['recommended_prompts']}")
    
    print(f"\n📊 Circuit Statistics:")
    stats = report['complexity_metrics']
    print(f"   • Total Components: {stats['component_count']}")
    print(f"   • Component Types: {stats['component_types']}")  
    print(f"   • Unique Nodes: {stats['node_count']}")
    print(f"   • Active Components: {stats['breakdown']['active']}")
    print(f"   • Passive Components: {stats['breakdown']['passive']}")
    print(f"   • Power Components: {stats['breakdown']['power']}")
    print(f"   • Complexity Score: {stats['score']:.1f}")
    
    if report['datasheet_recommendations']['prompts']:
        print("\n🔔 DATASHEET UPLOAD PROMPTS:")
        print("=" * 50)
        for i, prompt in enumerate(report['datasheet_recommendations']['prompts'], 1):
            print(f"\n{i}. {prompt['priority'].upper()}: {prompt['component_type'].upper()}")
            print(f"   Reason: {prompt['reason']}")
            print(f"   Impact: {prompt['impact']}")
            print(f"   Suggested Parts: {', '.join(prompt['suggested_parts'][:3])}")
            print(f"   Example Files: {', '.join(prompt['example_datasheets'][:2])}")
    
    if report.get('recommendations'):
        print(f"\n💡 Design Recommendations:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
    
    print("\n" + "=" * 80)
    print("🎉 Demo Complete! The circuit complexity analyzer intelligently identifies")
    print("   when circuits are complex enough to benefit from datasheet uploads.")
    print("=" * 80)


if __name__ == "__main__":
    demo_intelligent_datasheet_prompting() 