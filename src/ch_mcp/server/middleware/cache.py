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
from ch_mcp.azure.document_blob_cache import DocumentBlobCache
from ch_mcp.azure.table_key_value import AzureTableStore

logger = logging.getLogger(__name__)

# Appended to the configured table name prefix to form the active cache table name.
# Changing __version__.cache_version causes a new table to be created and stale
# tables from prior versions to be deleted on next startup.
_CACHE_VERSION_SLUG = _ch_version.cache_version.replace(".", "")


def _active_cache_table(settings: ch_mcp.settings.Settings) -> str:
    """Return the active cache table name: '{prefix}{cache_version_slug}'."""
    return f"{settings.table_store_names.api_cache}{_CACHE_VERSION_SLUG}"


# Tools whose responses the middleware must not cache.
#
# ``get_document_content`` returns a signed URL that embeds its own short-lived
# JWT (10 min by default). Caching the *tool response* for the normal 24h
# window would hand back URLs whose signatures have already expired. The
# underlying document bytes are still cached permanently in Azure Blob
# Storage, so skipping the response cache here costs nothing — the tool body
# is just a cheap JWT-mint.
_UNCACHEABLE_TOOLS: tuple[str, ...] = ("get_document_content",)


# Process-level handle on the document blob cache, set while the MCP lifespan
# is active. The HTTP ``/documents/{token}`` route reads this to avoid needing
# its own Azure client setup. Left as ``None`` in stdio mode, where the HTTP
# route isn't mounted anyway.
_shared_document_blob_cache: DocumentBlobCache | None = None


def get_shared_document_blob_cache() -> DocumentBlobCache:
    """Return the process-wide document blob cache opened during server lifespan."""
    if _shared_document_blob_cache is None:
        raise RuntimeError(
            "Document blob cache is not initialised — "
            "the MCP lifespan must be active before the HTTP document route serves a request."
        )
    return _shared_document_blob_cache


@contextlib.asynccontextmanager
async def open_api_response_cache(
    settings: ch_mcp.settings.Settings,
) -> AsyncGenerator[tuple[AsyncKeyValue, DocumentBlobCache], None]:
    """Open the Azure backends used for caching.

    Yields a tuple ``(table_store, document_blob_cache)``:

    * ``table_store`` — short-lived tool-response cache (JSON values), backed
      by Azure Table Storage with client-side TTL enforcement.
    * ``document_blob_cache`` — **permanent** binary cache for Companies
      House document payloads, backed by Azure Blob Storage. Documents are
      immutable once filed, so this cache never expires entries.

    Manages the full Azure client lifecycle: opens all clients, creates the
    active table if needed, creates the document container if needed, and
    closes everything on exit.
    """
    azure_api = AzureAPI(settings.azure)
    active_table = _active_cache_table(settings)

    global _shared_document_blob_cache
    async with azure_api.lifespan():
        table_store = AzureTableStore(client=azure_api.table_service_client, table_name=active_table)
        doc_cache = await DocumentBlobCache.open(
            blob_service_client=azure_api.blob_service_client,
            container_name=settings.blob_store_names.document_content,
        )
        _shared_document_blob_cache = doc_cache
        try:
            async with table_store:
                yield (table_store, doc_cache)
        finally:
            _shared_document_blob_cache = None


class ChCachingMiddleware(Middleware):
    """Caching middleware that reads its backing store from lifespan_context.

    Registered at server construction time; the inner ``ResponseCachingMiddleware``
    is instantiated lazily on the first tool call, once the lifespan has stored
    the ``AsyncKeyValue`` under ``_cache_store``. Until then, calls pass through
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
            call_tool_settings={
                "ttl": self._ttl,
                "excluded_tools": list(_UNCACHEABLE_TOOLS),
            },
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
