"""Container-level health endpoint."""

from __future__ import annotations

import time
from datetime import datetime

import fastmcp
from starlette.requests import Request
from starlette.responses import JSONResponse

import ch_mcp

_START_T = time.monotonic()


async def _health(request: Request) -> JSONResponse:
    """Return a small liveness/uptime document for container probes."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "ch-mcp",
            "version": ch_mcp.__version__.__version__,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.monotonic() - _START_T,
        }
    )


def mount_health_router(mcp: fastmcp.FastMCP) -> None:
    """Attach ``GET /.container/health`` to the MCP server's HTTP app."""
    mcp.custom_route("/.container/health", methods=["GET"], include_in_schema=False)(_health)
