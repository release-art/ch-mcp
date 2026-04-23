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

# Tools whose responses must be cached under a tighter TTL than the global
# default. Companies House Document API pre-signed URLs expire ~60 seconds
# after issue, so we cap the cache window at 50s to leave a 10s safety margin
# for the caller's own fetch.
_SHORT_LIVED_TOOL_CACHE: dict[str, int] = {
    "get_document_url": 50,
}


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

    Registered at server construction time; the inner ``ResponseCachingMiddleware``
    wrappers are created lazily on the first tool call, once the lifespan has
    stored the ``AzureKeyValue`` under ``_cache_store``. Until then, calls pass
    through uncached.

    Two inner caches share the same store:

    1. A **short-TTL** cache scoped to the tools in
       :data:`_SHORT_LIVED_TOOL_CACHE` (e.g. ``get_document_url`` — its output
       is a pre-signed URL valid for ~60s).
    2. A **default-TTL** cache for every *other* tool.

    The filters on each inner are mutually exclusive, so a call matches at most
    one cache. Tools outside both sets fall through to ``call_next`` uncached.
    """

    _short_inner: ResponseCachingMiddleware | None
    _default_inner: ResponseCachingMiddleware | None

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._short_inner = None
        self._default_inner = None

    def _ensure_inners(
        self,
        context: MiddlewareContext,
    ) -> tuple[ResponseCachingMiddleware, ResponseCachingMiddleware] | None:
        if self._short_inner is not None and self._default_inner is not None:
            return (self._short_inner, self._default_inner)
        if context.fastmcp_context is None:
            return None
        store: AsyncKeyValue | None = context.fastmcp_context.lifespan_context.get("_cache_store")
        if store is None:
            return None
        short_tools = list(_SHORT_LIVED_TOOL_CACHE.keys())
        # All short-lived entries currently share a TTL; if that changes we'd
        # need one inner per distinct TTL. Assert the homogeneity to fail loud
        # if future edits break the assumption.
        short_ttl_values = set(_SHORT_LIVED_TOOL_CACHE.values())
        assert len(short_ttl_values) == 1, "mixed short-lived TTLs require one inner per TTL"
        short_ttl = next(iter(short_ttl_values))
        self._short_inner = ResponseCachingMiddleware(
            cache_storage=store,
            call_tool_settings={"ttl": short_ttl, "included_tools": short_tools},
        )
        self._default_inner = ResponseCachingMiddleware(
            cache_storage=store,
            call_tool_settings={"ttl": self._ttl, "excluded_tools": short_tools},
        )
        return (self._short_inner, self._default_inner)

    @override
    async def on_call_tool(
        self,
        context: MiddlewareContext[mcp.types.CallToolRequestParams],
        call_next: CallNext[mcp.types.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        inners = self._ensure_inners(context)
        if inners is None:
            return await call_next(context)
        short_inner, default_inner = inners

        # Chain: short → default → call_next. Each inner's include/exclude
        # filter is a no-op for non-matching tools and falls through to its
        # own call_next, so the chain delivers exactly-one cache hit on
        # overlapping ranges.
        async def _default(context: MiddlewareContext[mcp.types.CallToolRequestParams]) -> ToolResult:
            return await default_inner.on_call_tool(context, call_next)

        return await short_inner.on_call_tool(context, _default)
