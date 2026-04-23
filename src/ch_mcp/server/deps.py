"""Companies House API dependencies."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator

import ch_api
import jwt
from fastmcp.dependencies import Depends

import ch_mcp

logger = logging.getLogger(__name__)


class _JWTPageTokenSerializer:
    """HMAC-signed opaque wrapper around ch_api pagination tokens.

    Pagination tokens encode the caller's position in a paginated query. We
    sign them with the server's JWT secret so a client cannot mint arbitrary
    tokens or tamper with the embedded offset.
    """

    _secret: str

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def serialize(self, token: str) -> str:
        return jwt.encode({"tok": token}, self._secret, algorithm="HS256")

    def deserialize(self, token: str) -> str:
        payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        return payload["tok"]


def _build_settings(ch_settings: ch_mcp.settings.ChApiSettings) -> ch_api.ApiSettings:
    """Resolve ch_api.ApiSettings from our ChApiSettings."""
    if ch_settings.base_url is not None:
        base = str(ch_settings.base_url).rstrip("/")
        return ch_api.ApiSettings(api_url=base, identity_url=base)
    if ch_settings.use_sandbox:
        return ch_api.api_settings.TEST_API_SETTINGS
    return ch_api.api_settings.LIVE_API_SETTINGS


@contextlib.asynccontextmanager
async def get_ch_api() -> AsyncIterator[ch_api.Client]:
    """Build a fresh ``ch_api.Client`` scoped to a single tool invocation.

    Bound to the tool-call lifecycle rather than the server lifespan: each MCP
    request gets its own underlying ``httpx.AsyncClient``, opened on entry and
    closed on exit. This avoids ref-counted-lifespan races in stateless HTTP
    transport mode where server-lifespan teardown between requests could
    otherwise close a shared client mid-use.
    """
    settings = ch_mcp.settings.get_settings()
    client = ch_api.Client(
        credentials=ch_api.AuthSettings(api_key=settings.ch_api.api_key),
        settings=_build_settings(settings.ch_api),
        page_token_serializer=_JWTPageTokenSerializer(settings.server.jwt_secret_key),
    )
    async with client:
        yield client


ChApiDep = Depends(get_ch_api)
