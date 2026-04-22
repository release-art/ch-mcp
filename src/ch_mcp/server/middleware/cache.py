"""Caching middleware for the Companies House MCP server."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncGenerator

import mcp.types
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from key_value.aio.protocols.key_value import AsyncKeyValue
from typing_extensions import override

import ch_mcp.__version__ as _ch_version
import ch_mcp.settings
from ch_mcp.azure.api import AzureAPI
from ch_mcp.azure.table_key_value import AzureTableStore

logger = logging.getLogger(__name__)

# Appended to the configured table name prefix to form the active cache table name.
# Changing __version__.cache_version causes a new table to be created and stale
# tables from prior versions to be deleted on next startup.
_CACHE_VERSION_SLUG = _ch_version.cache_version.replace(".", "")


def _active_cache_table(settings: ch_mcp.settings.Settings) -> str:
    """Return the active cache table name: '{prefix}{cache_version_slug}'."""
    return f"{settings.table_store_names.api_cache}{_CACHE_VERSION_SLUG}"


@contextlib.asynccontextmanager
async def open_azure_cache(settings: ch_mcp.settings.Settings) -> AsyncGenerator[AsyncKeyValue, None]:
    """Open the Azure Table Store used for API response caching.

    Manages the full Azure client lifecycle: opens all Azure Storage clients,
    deletes stale cache tables from previous cache_version values, creates the
    active table if needed, and closes everything on exit.
    """
    azure_api = AzureAPI(settings.azure)
    active_table = _active_cache_table(settings)

    async with azure_api.lifespan():
        store = AzureTableStore(client=azure_api.table_service_client, table_name=active_table)
        async with store:
            yield store


class ChCachingMiddleware(Middleware):
    """Caching middleware that reads its backing store from lifespan_context.

    Registered at server construction time; the inner ResponseCachingMiddleware
    is created lazily on the first tool call, once the lifespan has stored the
    AzureTableStore under LIFESPAN_CONTEXT_KEY. Until then, calls pass through
    uncached.
    """

    _inner: ResponseCachingMiddleware | None

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._inner = None

    def _get_inner(self, context: MiddlewareContext) -> ResponseCachingMiddleware | None:
        if self._inner is not None:
            return self._inner
        if context.fastmcp_context is None:
            return None
        store: AsyncKeyValue | None = context.fastmcp_context.lifespan_context.get("_cache_store")
        if store is None:
            return None
        self._inner = ResponseCachingMiddleware(
            cache_storage=store,
            call_tool_settings={"ttl": self._ttl},
        )
        return self._inner

    @override
    async def on_call_tool(
        self,
        context: MiddlewareContext[mcp.types.CallToolRequestParams],
        call_next: CallNext[mcp.types.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        inner = self._get_inner(context)
        if inner is None:
            return await call_next(context)
        return await inner.on_call_tool(context, call_next)
