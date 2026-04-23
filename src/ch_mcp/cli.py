"""Typer CLI entry point for the Companies House MCP server.

Exposes two commands:

- ``serve``: run the HTTP transport under uvicorn.
- ``stdio``: run the stdio transport for local MCP clients.

Invoked as ``python -m ch_mcp <command>``.
"""

from __future__ import annotations

import logging
import os

import typer
import uvicorn

import ch_mcp

logger = logging.getLogger(__name__)

app = typer.Typer(pretty_exceptions_enable=False)


@app.callback(invoke_without_command=True)
def startup(ctx: typer.Context):
    """Startup callback that runs before any command."""
    ch_mcp.logging.configure()
    ch_mcp.telemetry.configure()
    logger.info("Ch Mcp CLI started.")


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
        "ch_mcp.uvcorn_app:get_http_app",
        host=host,
        port=port,
        log_config=ch_mcp.logging.get_config(),
        factory=True,
        reload=reload,
    )


@app.command()
def stdio() -> None:
    """Run the stdio transport for local MCP clients."""
    # Tools branch on this to adapt their output for stdio (no HTTP server
    # is running, so signed proxy URLs wouldn't resolve; fall back to raw
    # upstream URLs where applicable).
    os.environ["CH_MCP_TRANSPORT"] = "stdio"
    mcp = ch_mcp.server.get_server()
    mcp.run()


if __name__ == "__main__":
    app()
