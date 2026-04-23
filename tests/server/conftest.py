import contextlib
import os
import pathlib

import ch_api
import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.server.auth import AccessToken
from key_value.aio.stores.memory import MemoryStore

import ch_mcp
from ch_mcp.server.auth import scopes as auth_scopes

_MOCK_CACHE_DIR = pathlib.Path(__file__).parent.parent / "mock_ch_api_cache"


def pytest_collection_modifyitems(config, items):
    """Skip tool-call tests when no CH_API_API_KEY is set and no cached fixtures exist for the test.

    Granularity is per-test-function: a new test added to a module that
    already has cache data for other tests still skips until the new test's
    own fixture directory exists.
    """
    has_key = bool(os.environ.get("CH_API_API_KEY") and os.environ["CH_API_API_KEY"] != "placeholder-no-live-calls")
    if has_key:
        return
    for item in items:
        basename = item.fspath.basename
        if not (basename.startswith("test_") and basename.endswith("_simple.py")):
            continue
        # `test_tools` only enumerates MCP tool metadata — no API call — so
        # never needs a cache fixture.
        if item.name == "test_tools":
            continue
        # MockChApi stores fixtures at mock_ch_api_cache/<module>.py/<test_name>/*.json
        per_test_cache = _MOCK_CACHE_DIR / basename / item.name
        if not per_test_cache.exists():
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        f"No CH_API_API_KEY set and no cached fixtures under"
                        f" tests/mock_ch_api_cache/{basename}/{item.name}/ —"
                        f" set CH_API_API_KEY on first run to populate."
                    )
                )
            )


@pytest.fixture
def resources_dir() -> pathlib.Path:
    out = pathlib.Path(__file__).parent / "resources"
    assert out.is_dir(), f"Resources directory not found at {out}"
    return out.resolve()


class _MemoryDocumentBlobCache:
    """In-memory stand-in for ``DocumentBlobCache`` used in tests.

    The MCP tool for document downloads doesn't touch the cache itself (it
    only mints a signed URL). The cache is only hit by the Starlette
    ``/documents/{token}`` route, so in the tool-call tests here the cache
    is an inert stand-in — present so the lifespan shape matches, but never
    read from or written to.
    """

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], bytes] = {}

    async def get(self, document_id: str, content_type: str) -> bytes | None:
        return self._data.get((document_id, content_type))

    async def put(self, document_id: str, content_type: str, data: bytes) -> None:
        self._data[(document_id, content_type)] = data


@pytest.fixture(autouse=True)
def mock_azure_cache(mocker):
    """Replace the Azure cache backends with in-memory stand-ins.

    Patches ``open_api_response_cache`` so tests run without real Azure
    infrastructure. Returns a tuple of (``MemoryStore`` table cache,
    in-memory ``DocumentBlobCache``).
    """

    doc_cache = _MemoryDocumentBlobCache()

    @contextlib.asynccontextmanager
    async def _mock(_settings):
        yield (MemoryStore(), doc_cache)

    mocker.patch("ch_mcp.server.middleware.cache.open_api_response_cache", _mock)
    return doc_cache


@pytest.fixture(autouse=True)
def original_client_cls():
    """Original ch_api Client class."""
    return ch_api.Client


@pytest.fixture(autouse=True)
def mock_ch_api(mocker, original_client_cls, caching_mock_api):
    """Mock ch_api.Client with a caching recorder that backs the real API on misses.

    Set CH_API_API_KEY in the environment to populate tests/mock_ch_api_cache/ on
    first run; afterwards tests run fully offline from the cached fixtures.
    """
    real_client = original_client_cls(
        credentials=ch_api.AuthSettings(api_key=os.environ.get("CH_API_API_KEY", "placeholder-no-live-calls")),
    )
    mock_client = caching_mock_api(api_implementation=real_client)
    mocker.patch("ch_api.Client", return_value=mock_client)
    return mock_client


@pytest.fixture
def oauth_scopes() -> list[str]:
    """OAuth scopes granted to the test client.

    Override this fixture in individual tests or test modules to test scope
    restrictions. The default grants full read access so existing tests pass
    unchanged.
    """
    return [auth_scopes.CH_API_RO]


@pytest.fixture(autouse=True)
def mock_auth_components(mocker, oauth_scopes):
    """Mock authentication components for in-memory transport testing."""
    from fastmcp.server.auth.providers.debug import DebugTokenVerifier

    mock_provider = DebugTokenVerifier(scopes=oauth_scopes)
    mocker.patch(
        "ch_mcp.server.auth.provider.get_auth_provider",
        return_value=mock_provider,
    )

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
    return ch_mcp.server.get_server()


@pytest_asyncio.fixture
async def mcp_client(mcp_app):
    async with Client(transport=mcp_app) as mcp_client:
        yield mcp_client
