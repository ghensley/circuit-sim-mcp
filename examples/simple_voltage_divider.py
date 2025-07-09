#!/usr/bin/env python3
"""Example: Simple voltage divider circuit using the MCP FastMCP server."""

import asyncio
import json
from circuit_sim_mcp.server import CircuitSimServer


def extract_json_content(result):
    """Extract content from FastMCP tool call result."""
    # FastMCP returns a list of TextContent objects, each with a .text attribute
    if isinstance(result, list) and result:
        for item in result:
            if hasattr(item, 'text'):
                try:
                    return json.loads(item.text)
                except Exception:
                    return item.text
    elif hasattr(result, 'text'):
        # Direct TextContent object
        try:
            return json.loads(result.text)
        except Exception:
            return result.text
    else:
        # Try to return as-is
        return result


async def main():
    """Run the voltage divider example using FastMCP tool calls."""
    sim_server = CircuitSimServer()
    server = sim_server.server

    print("Creating voltage divider circuit...")
    components = [
        {
            "type": "voltage_source",
            "name": "V1",
            "voltage": 10.0,
            "nodes": ["vin", "0"],
            "source_type": "DC"
        },
        {
            "type": "resistor",
            "name": "R1",
            "resistance": 1000.0,
            "nodes": ["vin", "vout"]
        },
        {
            "type": "resistor",
            "name": "R2",
            "resistance": 1000.0,
            "nodes": ["vout", "0"]
        }
    ]
    result = await server.call_tool("create_circuit", {"name": "voltage_divider", "components": components})
    print(f"Circuit creation result: {json.dumps(extract_json_content(result), indent=2)}")

    print("\nPerforming DC analysis...")
    dc_result = await server.call_tool("simulate_dc", {"circuit_name": "voltage_divider", "output_nodes": ["vin", "vout", "0"]})
    print(f"DC analysis result: {json.dumps(extract_json_content(dc_result), indent=2)}")

    print("\nPerforming AC analysis...")
    ac_result = await server.call_tool(
        "simulate_ac",
        {
            "circuit_name": "voltage_divider",
            "start_freq": 1.0,
            "stop_freq": 1e6,
            "num_points": 50,
            "output_nodes": ["vout"]
        }
    )
    print(f"AC analysis result: {json.dumps(extract_json_content(ac_result), indent=2)}")

    print("\nGetting circuit information...")
    info_result = await server.call_tool("get_circuit_info", {"circuit_name": "voltage_divider"})
    print(f"Circuit info: {json.dumps(extract_json_content(info_result), indent=2)}")

    print("\nListing all circuits...")
    list_result = await server.call_tool("list_circuits", {})
    print(f"Circuit list: {json.dumps(extract_json_content(list_result), indent=2)}")

if __name__ == "__main__":
    asyncio.run(main()) 