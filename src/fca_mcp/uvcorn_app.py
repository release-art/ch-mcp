from __future__ import annotations

import logging
import time
from datetime import datetime

from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import fca_mcp

logger = logging.getLogger(__name__)
START_T = time.monotonic()


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "FCA MCP Server",
            "version": fca_mcp.__version__.__version__,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.monotonic() - START_T,
        }
    )


def get_http_app() -> Starlette:
    """Get the FastAPI application instance."""
    settings = fca_mcp.settings.get_settings()
    logger.info("Creating FastAPI application...")
    mcp = fca_mcp.server.get_server()
    mcp.custom_route("/.container/health", methods=["GET"], include_in_schema=False)(health)
    if settings.auth0.interactive_client_id:
        logger.info("Interactive client ID configured, including interactive UI routes")
        fca_mcp.http.mount_interactive_router(mcp)

    mcp_app = mcp.http_app(
        path="/",
        middleware=[
            StarletteMiddleware(
                StarletteCORSMiddleware,
                allow_origins=["*"],  # Allow all origins; use specific origins for security
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                allow_headers=[
                    "mcp-protocol-version",
                    "mcp-session-id",
                    "Authorization",
                    "Content-Type",
                ],
                expose_headers=["mcp-session-id"],
            )
        ],
        stateless_http=True,
    )
    return mcp_app
