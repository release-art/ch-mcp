"""Test configuration."""

from __future__ import annotations

import pytest

import fca_mcp

pytest_plugins = [
    "tests.test_plugins.mock_client",
]


@pytest.fixture
def test_settings() -> fca_mcp.settings.Settings:
    """Test settings fixture."""
    return fca_mcp.settings.Settings(
        environment="development",
        debug=True,
        azure=fca_mcp.settings.AzureSettings(
            credential="none",
            storage_connection_string="DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=dGVzdGtleQ==;EndpointSuffix=core.windows.net",
        ),
        blob_store_names=fca_mcp.settings.BlobStoreNamesSettings(
            auth0_clients="test-auth0-clients",
        ),
        table_store_names=fca_mcp.settings.TableStoreNamesSettings(
            api_cache="apicache",
        ),
        cache=fca_mcp.settings.CacheSettings(
            ttl_seconds=3600,
        ),
        auth0=fca_mcp.settings.RemoteAuth0Settings(
            domain="test.auth0.com",
            audience="https://test-api.example.com",
        ),
        fca_api=fca_mcp.settings.FcaApiSettings(
            username="test.user@example.com",
            key="test_fca_api_key_12345",
        ),
        server=fca_mcp.settings.ServerSettings(
            host="127.0.0.1",
            port=8000,
            base_url="http://localhost:8000",
            jwt_secret_key="test-jwt-secret",
        ),
        logging=fca_mcp.settings.LoggingSettings(
            level="DEBUG",
            format="text",
        ),
        cors_origins=["http://localhost:3000", "http://localhost:8000"],
        api_version="v1",
    )


@pytest.fixture(autouse=True)
def get_test_settings(mocker, test_settings: fca_mcp.settings.Settings):
    """Fixture to get test settings."""
    mocker.patch("fca_mcp.settings.get_settings", return_value=test_settings)
