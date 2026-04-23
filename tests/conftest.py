"""Test configuration."""

from __future__ import annotations

import os

import pytest

import ch_mcp

pytest_plugins = [
    "tests.test_plugins.mock_client",
]


@pytest.fixture
def test_settings() -> ch_mcp.settings.Settings:
    """Test settings fixture."""
    return ch_mcp.settings.Settings(
        environment="development",
        debug=True,
        azure=ch_mcp.settings.AzureSettings(
            credential="none",
            storage_connection_string="DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=dGVzdGtleQ==;EndpointSuffix=core.windows.net",
        ),
        blob_store_names=ch_mcp.settings.BlobStoreNamesSettings(
            auth0_clients="test-auth0-clients",
        ),
        table_store_names=ch_mcp.settings.TableStoreNamesSettings(
            api_cache="apicache",
        ),
        cache=ch_mcp.settings.CacheSettings(
            ttl_seconds=3600,
        ),
        auth0=ch_mcp.settings.RemoteAuth0Settings(
            domain="test.auth0.com",
            audience="https://test-api.example.com",
        ),
        ch_api=ch_mcp.settings.ChApiSettings(
            api_key=os.environ.get("CH_API_API_KEY", "test_ch_api_key_12345"),
        ),
        server=ch_mcp.settings.ServerSettings(
            host="127.0.0.1",
            port=8000,
            base_url="http://localhost:8000",
            jwt_secret_key="test-jwt-secret",
        ),
        logging=ch_mcp.settings.LoggingSettings(
            level="DEBUG",
            format="text",
        ),
        cors_origins=["http://localhost:3000", "http://localhost:8000"],
        api_version="v1",
    )


@pytest.fixture(autouse=True)
def get_test_settings(mocker, test_settings: ch_mcp.settings.Settings):
    """Fixture to get test settings."""
    mocker.patch("ch_mcp.settings.get_settings", return_value=test_settings)
