"""MCP server implementation."""

from __future__ import annotations

import logging

import fastmcp
from fastmcp.server.auth import restrict_tag
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware import AuthMiddleware, Middleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from mcp.types import Icon

import ch_mcp

logger = logging.getLogger(__name__)

from . import auth, companies, deps, filings, middleware, officers, psc, search, types


@lifespan
async def mcp_lifespan(mcp_app: fastmcp.FastMCP):
    """Open shared resources for the server's lifetime.

    Holds the Azure Table Storage API response cache. The ``ch_api.Client`` is
    **not** opened here — it is created per-tool-call via ``deps.get_ch_api``
    so that its httpx session lifecycle is bound to the MCP call scope rather
    than the ref-counted server lifespan (which can tear down between requests
    in stateless HTTP mode).
    """
    settings = ch_mcp.settings.get_settings()
    async with middleware.cache.open_azure_cache(settings) as cache_store:
        logger.info("Server %s initialized successfully", mcp_app)
        yield {"_cache_store": cache_store}
    logger.info("Server shutdown complete")


def get_server() -> fastmcp.FastMCP:
    """Build the composed FastMCP server.

    Mounts the five sub-servers (search, companies, officers, psc, filings),
    wires up the middleware stack, and installs the configured auth provider.
    """
    settings = ch_mcp.settings.get_settings()
    auth_provider = auth.provider.get_auth_provider()
    logger.info(f"Building server with auth provider {auth_provider!r}")

    middleware_stack: list[Middleware | None] = [
        (
            # Only gate tools on the companies-house-api:read scope when an auth provider is configured.
            # With AUTH0_MODE=none there is no access token, and restrict_tag would reject
            # every tagged tool — which is all of them — hiding them from tools/list.
            AuthMiddleware(auth=restrict_tag(auth.tags.CH_API_RO, scopes=[auth.scopes.CH_API_RO]))
            if auth_provider is not None
            else None
        ),
        ErrorHandlingMiddleware(include_traceback=settings.debug),
        RateLimitingMiddleware(),
        LoggingMiddleware(),
        middleware.cache.ChCachingMiddleware(ttl_seconds=settings.cache.ttl_seconds),
    ]
    main = fastmcp.FastMCP(
        f"Release.art public MCP v{ch_mcp.__version__.__version__}",
        lifespan=mcp_lifespan,
        website_url="https://www.release.art/",
        icons=[
            Icon(
                src="https://static.release.art/assets/icons/brandmark_blue.svg",
                mimeType="image/svg+xml",
                sizes=["any"],
            )
        ],
        on_duplicate="error",
        strict_input_validation=True,
        auth=auth_provider,
        middleware=[el for el in middleware_stack if el is not None],
    )
    main.mount(search.get_server())
    main.mount(companies.get_server())
    main.mount(officers.get_server())
    main.mount(psc.get_server())
    main.mount(filings.get_server())
    return main
