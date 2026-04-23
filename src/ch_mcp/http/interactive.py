"""Interactive web UI for the FCA MCP server.

Provides a browser-based interface with Auth0 SPA SDK login
and tool explorer that calls MCP tools via JSON-RPC.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fastmcp
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
    auth0 = settings.auth0
    assert not isinstance(auth0, ch_mcp.settings.NoneAuth0Settings), (
        "Interactive UI requires AUTH0_MODE=remote or proxy"
    )
    return JSONResponse(
        {
            "auth0_domain": auth0.domain,
            "auth0_audience": auth0.audience,
            "auth0_client_id": auth0.interactive_client_id,
        }
    )


# @interactive_router.get("/", response_class=HTMLResponse)
async def interactive_ui(request: Request) -> HTMLResponse:
    """Serve the interactive MCP tool explorer."""
    settings = ch_mcp.settings.get_settings()
    auth0 = settings.auth0
    assert not isinstance(auth0, ch_mcp.settings.NoneAuth0Settings), (
        "Interactive UI requires AUTH0_MODE=remote or proxy"
    )
    base_url = str(request.base_url).rstrip("/")

    template = _jinja_env.get_template("interactive.html")
    content = template.render(
        domain=auth0.domain,
        audience=auth0.audience,
        client_id=auth0.interactive_client_id or "",
        mcp_url=f"{base_url}",
    )

    return HTMLResponse(content=content)


def mount_interactive_router(mcp: fastmcp.FastMCP) -> None:
    """Attach the interactive OAuth web-UI routes (``/interactive`` + config)."""
    mcp.custom_route("/interactive/config", methods=["GET"], include_in_schema=False)(interactive_config)
    mcp.custom_route("/interactive", methods=["GET"], include_in_schema=False)(interactive_ui)
