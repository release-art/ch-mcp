"""HTTP route that serves Companies House document payloads by signed URL.

The ``get_document_content`` MCP tool (in HTTP transport mode) mints a JWT
carrying ``(document_id, content_type, exp)`` signed with the server's
``SERVER_JWT_SECRET_KEY`` and returns a URL of the form
``{SERVER_BASE_URL}/documents/{token}``.

This module provides the matching ``GET`` handler:

1. Decode the token, rejecting tampered / expired ones.
2. Look up the bytes in the shared blob cache.
3. On miss, fetch from Companies House, store in the cache, then serve.
4. Stream back with the requested ``Content-Type`` and a filename hint.
"""

from __future__ import annotations

import logging

import ch_api
import fastmcp
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

import ch_mcp
from ch_mcp.server import deps, document_url
from ch_mcp.server.middleware.cache import get_shared_document_blob_cache

logger = logging.getLogger(__name__)

DOCUMENT_ROUTE_PATH = "/documents/{token}"


async def _fetch_document_bytes(
    document_id: str,
    content_type: str,
) -> bytes | None:
    """Fetch the document from Companies House using a fresh ch_api.Client."""
    settings = ch_mcp.settings.get_settings()
    client = ch_api.Client(
        credentials=ch_api.AuthSettings(api_key=settings.ch_api.api_key),
        settings=deps._build_settings(settings.ch_api),
        page_token_serializer=deps._JWTPageTokenSerializer(settings.server.jwt_secret_key),
    )
    async with client:
        async with client.get_document_content(document_id, content_type=content_type) as response:
            if response is None:
                return None
            response.raise_for_status()
            return response.content


async def get_document(request: Request) -> Response:
    """Serve a document payload to a caller holding a valid signed URL."""
    token = request.path_params["token"]
    settings = ch_mcp.settings.get_settings()
    try:
        claims = document_url.verify_document_token(
            secret=settings.server.jwt_secret_key,
            token=token,
        )
    except document_url.InvalidDocumentTokenError as e:
        logger.info("Rejecting document download: %s", e)
        return PlainTextResponse(f"Invalid or expired document token: {e}", status_code=403)

    doc_cache = get_shared_document_blob_cache()
    payload = await doc_cache.get(claims.document_id, claims.content_type)
    if payload is None:
        logger.info(
            "Document cache miss for %s (%s); fetching from upstream.",
            claims.document_id,
            claims.content_type,
        )
        payload = await _fetch_document_bytes(claims.document_id, claims.content_type)
        if payload is None:
            return PlainTextResponse(f"Document not found: {claims.document_id}", status_code=404)
        max_bytes = settings.cache.max_document_bytes
        if len(payload) > max_bytes:
            logger.warning(
                "Document %s (%s) is %d bytes, exceeds max_document_bytes=%d",
                claims.document_id,
                claims.content_type,
                len(payload),
                max_bytes,
            )
            return PlainTextResponse(
                f"Document is too large to serve through this MCP ({len(payload):,} bytes; cap is {max_bytes:,}).",
                status_code=413,
            )
        await doc_cache.put(claims.document_id, claims.content_type, payload)

    return Response(
        content=payload,
        media_type=claims.content_type,
        headers={
            # Encourage browsers to download with a recognisable filename.
            "Content-Disposition": f'inline; filename="{claims.document_id}"',
        },
    )


def mount_documents_router(mcp: fastmcp.FastMCP) -> None:
    """Attach ``GET /documents/{token}`` to the MCP server's HTTP app."""
    mcp.custom_route(DOCUMENT_ROUTE_PATH, methods=["GET"], include_in_schema=False)(get_document)
