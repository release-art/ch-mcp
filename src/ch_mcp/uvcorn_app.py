"""HTTP app factory for the uvicorn entrypoint."""

from __future__ import annotations

import logging

from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from starlette.routing import Route

import ch_mcp

logger = logging.getLogger(__name__)

# Canonical MCP endpoint path, plus any aliases that point at the same ASGI
# handler. Clients that hard-code one path or the other both work.
MCP_PATH = "/"
MCP_ALIASES: tuple[str, ...] = ("/mcp",)


def get_http_app() -> Starlette:
    """Compose the Starlette app: MCP plus any enabled HTTP side-routes."""
    mcp = ch_mcp.server.get_server()

    # Each HTTP module owns its own ``mount_*_router`` that hangs routes off the
    # MCP instance via ``mcp.custom_route``. Keep this block a straight list of
    # "which HTTP features are wired on".
    ch_mcp.http.mount_landing_router(mcp)
    ch_mcp.http.mount_health_router(mcp)
    ch_mcp.http.mount_documents_router(mcp)

    app = mcp.http_app(
        path=MCP_PATH,
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
    _install_mcp_aliases(app, canonical=MCP_PATH, aliases=MCP_ALIASES)
    return app


def _install_mcp_aliases(app: Starlette, *, canonical: str, aliases: tuple[str, ...]) -> None:
    """Expose the MCP endpoint at multiple paths simultaneously.

    FastMCP's ``http_app(path=...)`` only accepts a single canonical path,
    but returns a stock Starlette app. We locate the canonical MCP route
    and append a fresh ``Route`` for each alias that reuses the same ASGI
    endpoint and HTTP-method set — no redirects, both paths serve the MCP
    session manager directly.
    """
    canonical_route: Route | None = next(
        (r for r in app.routes if isinstance(r, Route) and r.path == canonical),
        None,
    )
    if canonical_route is None:
        raise RuntimeError(f"Canonical MCP route {canonical!r} not found on Starlette app")

    for alias in aliases:
        app.routes.append(
            Route(
                alias,
                endpoint=canonical_route.endpoint,
                methods=list(canonical_route.methods or []),
            )
        )
        logger.info("Mounted MCP endpoint alias %s → %s", alias, canonical)
