"""MCP server implementation."""

from __future__ import annotations

import asyncio
import logging

import fastmcp
import fca_api
import jwt
from fastmcp.server.auth import restrict_tag
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware import AuthMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from mcp.types import Icon

import fca_mcp

logger = logging.getLogger(__name__)

from . import app, auth, deps, firms, funds, individuals, markets, middleware, search, types


class _JWTPageTokenSerializer:
    _secret: str

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def serialize(self, token: str) -> str:
        return jwt.encode({"tok": token}, self._secret, algorithm="HS256")

    def deserialize(self, token: str) -> str:
        payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        return payload["tok"]


@lifespan
async def mcp_lifespan(mcp_app: fastmcp.FastMCP):
    """Open shared resources for the server's lifetime.

    Opens Azure Table Storage for API response caching and the FCA API client,
    exposing both via lifespan_context. The FcaCachingMiddleware (registered at
    server construction) reads the cache store from lifespan_context on first use.
    """
    settings = fca_mcp.settings.get_settings()

    async with middleware.cache.open_azure_cache(settings) as cache_store:
        client = fca_api.async_api.Client(
            (settings.fca_api.username, settings.fca_api.key),
            page_token_serializer=_JWTPageTokenSerializer(settings.server.jwt_secret_key),
        )
        logger.info("Server %s initialized successfully", mcp_app)
        async with client:
            yield {
                "fca_app": app.FcaApp(fca_api=client),
                "_cache_store": cache_store,
            }

    logger.info("Server shutdown complete")


def get_server() -> fastmcp.FastMCP:
    """Build the composed FastMCP server.

    Mounts the five sub-servers (search, firms, funds, individuals,
    markets), wires up the middleware stack, and installs the configured
    auth provider.
    """
    settings = fca_mcp.settings.get_settings()
    main = fastmcp.FastMCP(
        f"Release.art public MCP v{fca_mcp.__version__.__version__}",
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
        auth=auth.provider.get_auth_provider(),
        middleware=[
            AuthMiddleware(auth=restrict_tag(auth.tags.FCA_API_RO, scopes=[auth.scopes.FCA_API_RO])),
            ErrorHandlingMiddleware(include_traceback=settings.debug),
            RateLimitingMiddleware(),
            LoggingMiddleware(),
            middleware.cache.FcaCachingMiddleware(ttl_seconds=settings.cache.ttl_seconds),
        ],
    )
    main.mount(search.get_server())
    main.mount(firms.get_server())
    main.mount(funds.get_server())
    main.mount(individuals.get_server())
    main.mount(markets.get_server())
    return main
