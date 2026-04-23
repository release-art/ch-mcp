"""Tests for the signed-URL document token helpers."""

import pytest

from ch_mcp.server.document_url import (
    InvalidDocumentTokenError,
    mint_document_token,
    verify_document_token,
)

_SECRET = "unit-test-secret-unit-test-secret"


def test_mint_and_verify_roundtrip():
    token = mint_document_token(
        secret=_SECRET,
        document_id="DOC1",
        content_type="application/pdf",
        ttl_seconds=60,
    )
    claims = verify_document_token(secret=_SECRET, token=token)
    assert claims.document_id == "DOC1"
    assert claims.content_type == "application/pdf"


def test_verify_rejects_wrong_secret():
    token = mint_document_token(
        secret=_SECRET,
        document_id="DOC1",
        content_type="application/pdf",
        ttl_seconds=60,
    )
    with pytest.raises(InvalidDocumentTokenError):
        verify_document_token(secret="different-secret-" * 2, token=token)


def test_verify_rejects_expired_token():
    token = mint_document_token(
        secret=_SECRET,
        document_id="DOC1",
        content_type="application/pdf",
        ttl_seconds=-1,  # already expired
    )
    with pytest.raises(InvalidDocumentTokenError):
        verify_document_token(secret=_SECRET, token=token)


def test_verify_rejects_garbage():
    with pytest.raises(InvalidDocumentTokenError):
        verify_document_token(secret=_SECRET, token="not-a-jwt")
