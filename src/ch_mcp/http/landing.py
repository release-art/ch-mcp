"""Static HTML landing page served on ``GET /``.

The MCP ``streamable-http`` endpoint also lives at ``/`` but only accepts
``POST``/``DELETE``. Starlette's router treats path and method
independently, so a ``GET`` ``Route`` at the same path coexists cleanly —
``POST`` flows to the MCP session manager, ``GET`` flows to this landing
handler.

The template directory comes from :attr:`ServerSettings.http_resources_dir`
so operators can override it to serve a custom-branded landing page without
forking the package.
"""

from __future__ import annotations

import functools
import logging

import fastmcp
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse

import ch_mcp

logger = logging.getLogger(__name__)


@functools.cache
def _jinja_env_for(resources_dir: str) -> Environment:
    """Cache one Jinja environment per resource directory.

    Settings are resolved lazily (inside the request handler) so that the
    ``http_resources_dir`` override is honoured, but constructing an
    ``Environment`` for every request would be wasteful. ``functools.cache``
    gives us an environment per distinct resources path, which is what we
    want — in practice a single value for the whole process lifetime.
    """
    from pathlib import Path

    return Environment(
        loader=FileSystemLoader(Path(resources_dir)),
        autoescape=select_autoescape(("html", "htm")),
    )


async def _landing(request: Request) -> HTMLResponse:
    settings = ch_mcp.settings.get_settings()
    env = _jinja_env_for(str(settings.server.http_resources_dir))
    template = env.get_template("landing.html")
    body = template.render(
        version=ch_mcp.__version__.__version__,
        website_url=str(settings.server.website_url),
        icon_url=str(settings.server.icon_url),
    )
    return HTMLResponse(body)


def mount_landing_router(mcp: fastmcp.FastMCP) -> None:
    """Attach ``GET /`` — a small human-readable landing page."""
    mcp.custom_route("/", methods=["GET"], include_in_schema=False)(_landing)
    mcp.custom_route("/mcp", methods=["GET"], include_in_schema=False)(_landing)
