#!/usr/bin/env python3
"""Example: Non-inverting amplifier using datasheet-based op-amp components."""

import asyncio
import json
from circuit_sim_mcp.server import CircuitSimServer


def extract_json_content(result):
    """Extract content from FastMCP tool call result."""
    if isinstance(result, list) and result:
        for item in result:
            if hasattr(item, 'text'):
                try:
                    return json.loads(item.text)
                except Exception:
                    return item.text
    elif hasattr(result, 'text'):
        try:
            return json.loads(result.text)
        except Exception:
            return result.text
    else:
        return result


async def main():
    """Demonstrate datasheet-based component usage in circuit design."""
    sim_server = CircuitSimServer()
    server = sim_server.server

    print("=== Circuit Simulation with Datasheet Components ===\n")

    # Step 1: Search for available op-amps
    print("1. Searching for available op-amps...")
    search_result = await server.call_tool("search_components", {
        "component_type": "operational amplifier"
    })
    search_data = extract_json_content(search_result)
    
    if search_data.get('success'):
        print(f"Found {search_data['results_count']} op-amps:")
        for comp in search_data['components'][:3]:  # Show first 3
            print(f"  - {comp['part_number']} ({comp['manufacturer']}): {comp['description']}")
    
    # Step 2: Get detailed datasheet for LM741
    print("\n2. Getting detailed datasheet for LM741...")
    datasheet_result = await server.call_tool("get_component_datasheet", {
        "part_number": "LM741"
    })
    datasheet_data = extract_json_content(datasheet_result)
    
    if datasheet_data.get('success'):
        print("LM741 Specifications:")
        params = datasheet_data['parameters']
        print(f"  - Gain-Bandwidth: {params['gain_bandwidth_hz']/1e6:.1f} MHz")
        print(f"  - Slew Rate: {params['slew_rate_v_per_s']/1e6:.1f} V/µs") 
        print(f"  - Input Offset Voltage: {params['input_offset_voltage_v']*1000:.1f} mV")
        print(f"  - Supply Voltage Range: {params['supply_voltage_min_v']} to {params['supply_voltage_max_v']} V")

    # Step 3: Create non-inverting amplifier with datasheet components
    print("\n3. Creating non-inverting amplifier circuit with LM741...")
    components = [
        # Power supplies
        {
            "type": "voltage_source",
            "name": "VCC",
            "voltage": 15.0,
            "nodes": ["vcc", "0"],
            "source_type": "DC"
        },
        {
            "type": "voltage_source", 
            "name": "VEE",
            "voltage": -15.0,
            "nodes": ["vee", "0"],
            "source_type": "DC"
        },
        # Input signal
        {
            "type": "voltage_source",
            "name": "VIN",
            "voltage": 1.0,
            "nodes": ["vin", "0"],
            "source_type": "AC"
        },
        # Op-amp with datasheet parameters
        {
            "type": "opamp",
            "name": "U1",
            "part_number": "LM741",
            "nodes": ["vout", "vin", "vref", "vcc", "vee"]
        },
        # Feedback network (gain = 1 + R2/R1 = 11)
        {
            "type": "resistor",
            "name": "R1", 
            "resistance": 1000.0,
            "nodes": ["vref", "0"]
        },
        {
            "type": "resistor",
            "name": "R2",
            "resistance": 10000.0,
            "nodes": ["vout", "vref"]
        },
        # Load resistor
        {
            "type": "resistor",
            "name": "RL",
            "resistance": 10000.0,
            "nodes": ["vout", "0"]
        }
    ]

    circuit_result = await server.call_tool("create_datasheet_circuit", {
        "name": "noninv_amplifier",
        "components": components
    })
    circuit_data = extract_json_content(circuit_result)
    
    if circuit_data.get('success'):
        print(f"Circuit created successfully with {circuit_data['component_count']} components")
        for comp in circuit_data['components']:
            if comp['datasheet_loaded']:
                print(f"  ✓ {comp['name']}: {comp['part_number']} ({comp['manufacturer']})")
            else:
                print(f"  - {comp['name']}: Generic component")

    # Step 4: Validate circuit design
    print("\n4. Validating circuit design against datasheet specifications...")
    validation_result = await server.call_tool("validate_circuit_design", {
        "circuit_name": "noninv_amplifier"
    })
    validation_data = extract_json_content(validation_result)
    
    if validation_data.get('success'):
        print(f"Overall Status: {validation_data['overall_status'].upper()}")
        if validation_data['warnings']:
            print("Warnings:")
            for warning in validation_data['warnings']:
                print(f"  ⚠️  {warning}")
        
        for result in validation_data['validation_results']:
            if result.get('datasheet_available'):
                print(f"  ✓ {result['component']}: Validated against datasheet")

    # Step 5: Get optimization recommendations
    print("\n5. Getting optimization recommendations...")
    optimization_result = await server.call_tool("optimize_circuit_design", {
        "circuit_name": "noninv_amplifier",
        "optimization_goals": ["speed", "noise"]
    })
    optimization_data = extract_json_content(optimization_result)
    
    if optimization_data.get('success') and optimization_data['recommendations']:
        print("Optimization Recommendations:")
        for rec in optimization_data['recommendations']:
            print(f"  Current: {rec['current_component']}")
            print(f"  Alternatives: {', '.join(rec['alternatives'])}")
            print(f"  Reason: {rec['recommendation_reason']}")

    # Step 6: Perform AC analysis
    print("\n6. Performing AC analysis (frequency response)...")
    ac_result = await server.call_tool("simulate_ac", {
        "circuit_name": "noninv_amplifier",
        "start_freq": 1.0,
        "stop_freq": 1e7,
        "num_points": 50,
        "output_nodes": ["vout"]
    })
    ac_data = extract_json_content(ac_result)
    
    if ac_data.get('success'):
        results = ac_data['results']['data']
        print(f"AC Analysis completed with {len(results['frequency'])} frequency points")
        print(f"Frequency range: {ac_data['frequency_range'][0]:.1f} Hz to {ac_data['frequency_range'][1]:.0e} Hz")
        
        # Find gain at different frequencies
        frequencies = results['frequency']
        magnitudes = results['vout_magnitude']
        
        # DC gain (lowest frequency)
        dc_gain = magnitudes[0]
        print(f"DC Gain: {dc_gain:.2f} (expected: ~11 for non-inverting amplifier)")
        
        # 3dB bandwidth estimation
        gain_3db = dc_gain / 1.414  # -3dB point
        for i, mag in enumerate(magnitudes):
            if mag <= gain_3db:
                bandwidth_3db = frequencies[i]
                print(f"Estimated -3dB Bandwidth: {bandwidth_3db/1e6:.2f} MHz")
                break

    # Step 7: Show circuit information
    print("\n7. Circuit Summary:")
    info_result = await server.call_tool("get_circuit_info", {
        "circuit_name": "noninv_amplifier"
    })
    info_data = extract_json_content(info_result)
    
    if info_data.get('success'):
        print(f"Nodes: {', '.join(info_data['nodes'])}")
        print(f"SPICE Netlist Preview:")
        netlist_lines = info_data['netlist'].split('\n')
        for line in netlist_lines[:8]:  # Show first 8 lines
            print(f"  {line}")
        if len(netlist_lines) > 8:
            print(f"  ... ({len(netlist_lines)-8} more lines)")

    print("\n=== Analysis Complete ===")
    print("\nThis example demonstrated:")
    print("• Searching component datasheets")
    print("• Creating circuits with real component specifications") 
    print("• Validating designs against datasheet limits")
    print("• Getting optimization recommendations")
    print("• Performing frequency analysis with realistic parameters")


if __name__ == "__main__":
    asyncio.run(main()) 