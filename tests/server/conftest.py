import contextlib
import pathlib

import fca_api
import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.server.auth import AccessToken
from key_value.aio.stores.memory import MemoryStore

import fca_mcp
from fca_mcp.server.auth import scopes as auth_scopes


@pytest.fixture
def resources_dir() -> pathlib.Path:
    out = pathlib.Path(__file__).parent / "resources"
    assert out.is_dir(), f"Resources directory not found at {out}"
    return out.resolve()


@pytest.fixture(autouse=True)
def mock_azure_cache(mocker):
    """Replace the Azure Table cache backend with an in-memory store.

    Patches _open_azure_cache so tests run without real Azure infrastructure.
    """

    @contextlib.asynccontextmanager
    async def _mock(_settings):
        yield MemoryStore()

    mocker.patch("fca_mcp.server.middleware.cache.open_azure_cache", _mock)


@pytest.fixture(autouse=True)
def original_client_cls():
    """Original Client class."""
    return fca_api.async_api.Client


@pytest.fixture(autouse=True)
def mock_fca_api(mocker, original_client_cls, caching_mock_api):
    mock_client = caching_mock_api(
        api_implementation=original_client_cls(("developer@release.art", "1853090975e4fbb76d8811a8853971c2")),
    )
    mocker.patch("fca_api.async_api.Client", return_value=mock_client)
    return mock_client


@pytest.fixture
def oauth_scopes() -> list[str]:
    """OAuth scopes granted to the test client.

    Override this fixture in individual tests or test modules to test scope
    restrictions. The default grants full read access so existing tests pass
    unchanged.

    Example — deny access by removing all scopes::

        @pytest.fixture
        def oauth_scopes():
            return []

    Example — grant a custom scope::

        @pytest.fixture
        def oauth_scopes():
            return ["custom:scope"]
    """
    return [auth_scopes.FCA_API_RO]


@pytest.fixture(autouse=True)
def mock_auth_components(mocker, oauth_scopes):
    """Mock authentication components for in-memory transport testing.

    Patches two things so that the MCP AuthMiddleware works without real
    Auth0 / Azure infrastructure:

    1. ``get_auth_provider()`` → returns a ``DebugTokenVerifier`` so
       ``get_server()`` can be called without Azure credentials.
    2. ``get_access_token()`` → returns a synthetic ``AccessToken`` whose
       scopes match the ``oauth_scopes`` fixture, allowing the
       ``AuthMiddleware`` to evaluate ``restrict_tag`` checks.
    """
    from fastmcp.server.auth.providers.debug import DebugTokenVerifier

    # Replace the auth provider so get_server() doesn't need Azure / Auth0.
    mock_provider = DebugTokenVerifier(scopes=oauth_scopes)
    mocker.patch(
        "fca_mcp.server.auth.provider.get_auth_provider",
        return_value=mock_provider,
    )

    # Provide a synthetic token with the requested scopes.
    # AuthMiddleware calls get_access_token() (imported at module level in
    # fastmcp.server.middleware.authorization) so we patch it there.
    mock_token = AccessToken(
        token="test-token",
        client_id="test-client",
        scopes=oauth_scopes,
        expires_at=None,
        claims={},
    )
    mocker.patch(
        "fastmcp.server.middleware.authorization.get_access_token",
        return_value=mock_token,
    )

    return mock_token


@pytest.fixture
def mcp_app(mock_auth_components):
    """Create test MCP server with mocked authentication."""
    return fca_mcp.server.get_server()


@pytest_asyncio.fixture
async def mcp_client(mcp_app):
    async with Client(transport=mcp_app) as mcp_client:
        yield mcp_client
