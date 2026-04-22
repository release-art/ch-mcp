"""MCP server implementation."""

from __future__ import annotations

import logging

import ch_api
import fastmcp
import jwt
from fastmcp.server.auth import restrict_tag
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware import AuthMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from mcp.types import Icon

import ch_mcp

logger = logging.getLogger(__name__)

from . import app, auth, companies, deps, filings, middleware, officers, psc, search, types


class _JWTPageTokenSerializer:
    _secret: str

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def serialize(self, token: str) -> str:
        return jwt.encode({"tok": token}, self._secret, algorithm="HS256")

    def deserialize(self, token: str) -> str:
        payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        return payload["tok"]


def _build_ch_api_settings(ch_settings: ch_mcp.settings.ChApiSettings) -> ch_api.ApiSettings:
    """Resolve the ``ch_api.ApiSettings`` from our ``ChApiSettings``."""
    if ch_settings.base_url is not None:
        base = str(ch_settings.base_url).rstrip("/")
        return ch_api.ApiSettings(api_url=base, identity_url=base)
    if ch_settings.use_sandbox:
        return ch_api.api_settings.TEST_API_SETTINGS
    return ch_api.api_settings.LIVE_API_SETTINGS


@lifespan
async def mcp_lifespan(mcp_app: fastmcp.FastMCP):
    """Open shared resources for the server's lifetime.

    Opens Azure Table Storage for API response caching and the Companies House
    API client, exposing both via lifespan_context. The ChCachingMiddleware
    (registered at server construction) reads the cache store from
    lifespan_context on first use.
    """
    settings = ch_mcp.settings.get_settings()

    async with middleware.cache.open_azure_cache(settings) as cache_store:
        client = ch_api.Client(
            credentials=ch_api.AuthSettings(api_key=settings.ch_api.api_key),
            settings=_build_ch_api_settings(settings.ch_api),
            page_token_serializer=_JWTPageTokenSerializer(settings.server.jwt_secret_key),
        )
        logger.info("Server %s initialized successfully", mcp_app)
        async with client:
            yield {
                "ch_app": app.ChApp(ch_api=client),
                "_cache_store": cache_store,
            }

    logger.info("Server shutdown complete")


def get_server() -> fastmcp.FastMCP:
    """Build the composed FastMCP server.

    Mounts the five sub-servers (search, companies, officers, psc, filings),
    wires up the middleware stack, and installs the configured auth provider.
    """
    settings = ch_mcp.settings.get_settings()
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
        auth=auth.provider.get_auth_provider(),
        middleware=[
            AuthMiddleware(auth=restrict_tag(auth.tags.CH_API_RO, scopes=[auth.scopes.CH_API_RO])),
            ErrorHandlingMiddleware(include_traceback=settings.debug),
            RateLimitingMiddleware(),
            LoggingMiddleware(),
            middleware.cache.ChCachingMiddleware(ttl_seconds=settings.cache.ttl_seconds),
        ],
    )
    main.mount(search.get_server())
    main.mount(companies.get_server())
    main.mount(officers.get_server())
    main.mount(psc.get_server())
    main.mount(filings.get_server())
    return main
