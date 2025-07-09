# Circuit Simulation MCP Server

A Model Context Protocol (MCP) server that provides circuit simulation capabilities using PySpice. This server allows you to create, simulate, and analyze electronic circuits through a simple tool-based interface.

## Features

- **Circuit Creation**: Define circuits with various components (resistors, capacitors, inductors, voltage/current sources, diodes, transistors)
- **Multiple Analysis Types**: 
  - DC Analysis (steady-state)
  - AC Analysis (frequency response)
  - Transient Analysis (time-domain)
- **Circuit Management**: List circuits, get detailed information, export data
- **Visualization**: Generate plots of simulation results
- **SPICE Integration**: Uses PySpice for accurate circuit simulation

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Ngspice**: The underlying SPICE simulator
   - macOS: `brew install ngspice`
   - Ubuntu/Debian: `sudo apt-get install ngspice`
   - Windows: Download from [ngspice website](http://ngspice.sourceforge.net/)

### Install the Package

```bash
# Clone the repository
git clone <repository-url>
cd circuit-sim-mcp

# Install in development mode
pip install -e .
```

### Dependencies

The package will automatically install:
- `mcp` - Model Context Protocol Python SDK
- `pydantic` - Data validation
- `numpy` - Numerical computations
- `matplotlib` - Plotting (optional)

## Usage

### Running the MCP Server

The server can be run as a standalone MCP server:

```bash
python -m circuit_sim_mcp
```

### Using with MCP Clients

Configure your MCP client to use this server:

```json
{
  "mcpServers": {
    "circuit-sim": {
      "command": "python",
      "args": ["-m", "circuit_sim_mcp"],
      "env": {}
    }
  }
}
```

### Available Tools

1. **`create_circuit`** - Create a new circuit with components
2. **`simulate_dc`** - Perform DC analysis
3. **`simulate_ac`** - Perform AC analysis  
4. **`simulate_transient`** - Perform transient analysis
5. **`plot_results`** - Generate plots
6. **`export_data`** - Export simulation data
7. **`list_circuits`** - List all circuits
8. **`get_circuit_info`** - Get detailed circuit information

## Example

Here's a simple voltage divider example:

```python
import asyncio
from circuit_sim_mcp.server_basic import CircuitSimServer

async def main():
    sim_server = CircuitSimServer()
    server = sim_server.server

    # Create a voltage divider circuit
    components = [
        {
            "type": "voltage_source",
            "name": "V1",
            "voltage": 10.0,
            "nodes": ["vin", "gnd"],
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
            "nodes": ["vout", "gnd"]
        }
    ]
    
    # Create the circuit
    result = await server.call_tool("create_circuit", {
        "name": "voltage_divider", 
        "components": components
    })
    
    # Perform DC analysis
    dc_result = await server.call_tool("simulate_dc", {
        "circuit_name": "voltage_divider",
        "output_nodes": ["vin", "vout", "gnd"]
    })
    
    print(f"DC Analysis: {dc_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

See `examples/simple_voltage_divider.py` for a complete working example.

## Component Types

### Supported Components

- **Resistor**: `{"type": "resistor", "name": "R1", "resistance": 1000.0, "nodes": ["n1", "n2"]}`
- **Capacitor**: `{"type": "capacitor", "name": "C1", "capacitance": 1e-6, "nodes": ["n1", "n2"]}`
- **Inductor**: `{"type": "inductor", "name": "L1", "inductance": 1e-3, "nodes": ["n1", "n2"]}`
- **Voltage Source**: `{"type": "voltage_source", "name": "V1", "voltage": 5.0, "nodes": ["n1", "n2"], "source_type": "DC"}`
- **Current Source**: `{"type": "current_source", "name": "I1", "current": 1.0, "nodes": ["n1", "n2"], "source_type": "DC"}`
- **Diode**: `{"type": "diode", "name": "D1", "nodes": ["n1", "n2"], "model": "1N4148"}`
- **Transistor**: `{"type": "transistor", "name": "Q1", "transistor_type": "npn", "nodes": ["collector", "base", "emitter"], "model": "2N2222"}`

### Node Names

⚠️ **Important**: Node names cannot be Python keywords. Use descriptive names like:
- `vin`, `vout` (instead of `in`, `out`)
- `vcc`, `vdd`, `gnd` (instead of `class`, `def`, `if`)

## Branch Structure

This repository has two main branches with different feature sets:

### 🌟 `main` branch (Current - Basic Version)
- **Purpose**: Core circuit simulation functionality
- **Target**: Users who need basic circuit analysis
- **Features**: Essential circuit creation, simulation (DC/AC/Transient), and data export
- **Complexity**: Simple, focused, easy to understand and extend

### 🚀 `advanced-features` branch
- **Purpose**: Full-featured version with AI-powered analysis
- **Target**: Professional users and complex circuit design
- **Features**: Everything in main + intelligent datasheet prompting, complexity analysis, datasheet-based components
- **Complexity**: Advanced features for sophisticated circuit analysis

To access advanced features:
```bash
git checkout advanced-features
```

## Architecture

- **`server_basic.py`**: Basic MCP server implementation using FastMCP
- **`circuit.py`**: Circuit representation and component definitions
- **`simulator.py`**: PySpice integration and simulation engine
- **`__main__.py`**: Entry point for running the server

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Adding New Components

1. Add the component class to `circuit.py`
2. Update the `Component.from_dict()` method
3. Add netlist generation in `Circuit._component_to_netlist()`

## Troubleshooting

### PySpice Import Errors

If you get PySpice import errors:

1. Ensure ngspice is installed and in your PATH
2. Check architecture compatibility (x86_64 vs arm64)
3. Reinstall numpy and PySpice for your architecture:
   ```bash
   pip uninstall numpy PySpice
   pip install numpy PySpice
   ```

### Node Name Errors

If you get errors about node names being Python keywords, rename your nodes to avoid reserved words.

## Advanced Features

For advanced features like intelligent datasheet prompting, circuit complexity analysis, and datasheet-based components, check out the `advanced-features` branch:

```bash
git checkout advanced-features
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request 