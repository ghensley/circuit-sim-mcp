"""Entry point for the circuit simulation MCP server."""

from .server import CircuitSimServer


def main() -> None:
    """Run the MCP server using FastMCP."""
    sim_server = CircuitSimServer()
    sim_server.server.run(transport="stdio")


if __name__ == "__main__":
    main() 