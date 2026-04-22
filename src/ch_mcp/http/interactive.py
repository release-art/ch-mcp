"""Interactive web UI for the FCA MCP server.

Provides a browser-based interface with Auth0 SPA SDK login
and tool explorer that calls MCP tools via JSON-RPC.
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

import ch_mcp.settings

logger = logging.getLogger(__name__)

# interactive_router = fastapi.APIRouter(prefix="/interactive", tags=["Interactive"])

# Set up Jinja2 environment
_RESOURCES_DIR = Path(__file__).parent / "resources"
_jinja_env = Environment(
    loader=FileSystemLoader(_RESOURCES_DIR),
    autoescape=True,
)


# @interactive_router.get("/config")
async def interactive_config(request: Request) -> JSONResponse:
    """Return Auth0 config for the SPA SDK (public, non-secret values only)."""
    settings = ch_mcp.settings.get_settings()
    return JSONResponse(
        {
            "auth0_domain": settings.auth0.domain,
            "auth0_audience": settings.auth0.audience,
            "auth0_client_id": settings.auth0.interactive_client_id,
        }
    )


# @interactive_router.get("/", response_class=HTMLResponse)
async def interactive_ui(request: Request) -> HTMLResponse:
    """Serve the interactive MCP tool explorer."""
    settings = ch_mcp.settings.get_settings()
    base_url = str(request.base_url).rstrip("/")

    template = _jinja_env.get_template("interactive.html")
    content = template.render(
        domain=settings.auth0.domain,
        audience=settings.auth0.audience,
        client_id=settings.auth0.interactive_client_id or "",
        mcp_url=f"{base_url}",
    )

    return HTMLResponse(content=content)
