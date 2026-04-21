"""Typer CLI entry point for the FCA MCP server.

Exposes two commands:

- ``serve``: run the HTTP transport under uvicorn.
- ``stdio``: run the stdio transport for local MCP clients.

Invoked as ``python -m fca_mcp <command>``.
"""

from __future__ import annotations

import logging

import typer
import uvicorn

import fca_mcp

logger = logging.getLogger(__name__)

app = typer.Typer(pretty_exceptions_enable=False)


@app.callback(invoke_without_command=True)
def startup(ctx: typer.Context):
    """Startup callback that runs before any command."""
    fca_mcp.logging.configure()
    fca_mcp.telemetry.configure()
    logger.info("Fca Mcp CLI started.")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the HTTP transport under uvicorn."""
    logger.info("[HTTP] Starting server on %s:%s", host, port)
    logger.info(
        "[HTTP] Web UI: http://%s:%s",
        host,
        port,
    )
    uvicorn.run(
        "fca_mcp.uvcorn_app:get_http_app",
        host=host,
        port=port,
        log_config=fca_mcp.logging.get_config(),
        factory=True,
        reload=reload,
    )


@app.command()
def stdio() -> None:
    """Run the stdio transport for local MCP clients."""
    mcp = fca_mcp.server.get_server()
    mcp.run()


if __name__ == "__main__":
    app()
