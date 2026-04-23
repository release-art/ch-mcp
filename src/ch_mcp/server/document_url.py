"""Signed-URL helpers for the document-content HTTP endpoint.

Minting: ``get_document_content`` (in HTTP-transport mode) signs a compact
JWT claiming ``document_id`` and ``content_type``, valid for a short TTL.
The URL embeds the JWT and is returned to the MCP caller.

Verification: the ``/documents/{token}`` Starlette route decodes the JWT
with the server's secret, rejects expired or tampered tokens, and streams
the document bytes back.

The scheme mirrors how S3 pre-signed URLs work — the signature in the URL
*is* the authentication, so no Bearer header is required. This lets links
the LLM emits be used directly by browsers or other HTTP clients. CH
filings are already public record, so link leakage has limited downside;
the short TTL keeps the window small either way.
"""

from __future__ import annotations

import datetime

import jwt
import pydantic

# JWT with no signature is useless; HS256 is fine for process-local signing.
_ALG = "HS256"


class DocumentTokenClaims(pydantic.BaseModel):
    """Claims carried by a document-download signed URL."""

    document_id: str
    content_type: str
    # Standard JWT claim — seconds since epoch, UTC.
    exp: int


def mint_document_token(
    *,
    secret: str,
    document_id: str,
    content_type: str,
    ttl_seconds: int,
) -> str:
    """Return a signed JWT valid for ``ttl_seconds`` starting now."""
    exp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()) + ttl_seconds
    claims = {
        "document_id": document_id,
        "content_type": content_type,
        "exp": exp,
    }
    return jwt.encode(claims, secret, algorithm=_ALG)


class InvalidDocumentTokenError(Exception):
    """Raised when a ``/documents/{token}`` request carries a bad token."""


def verify_document_token(*, secret: str, token: str) -> DocumentTokenClaims:
    """Decode and validate a document-download token.

    Raises :class:`InvalidDocumentTokenError` on any failure (expired, tampered,
    missing fields). Never returns an unsigned or expired token.
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALG])
    except jwt.PyJWTError as e:
        raise InvalidDocumentTokenError(str(e)) from e
    try:
        return DocumentTokenClaims.model_validate(payload)
    except pydantic.ValidationError as e:
        raise InvalidDocumentTokenError(f"malformed claims: {e}") from e
