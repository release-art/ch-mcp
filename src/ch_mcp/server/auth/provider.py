"""FastMCP authentication module."""

from __future__ import annotations

import logging

from fastmcp.server.auth import AuthProvider

import ch_mcp
import ch_mcp.settings

from . import scopes

logger = logging.getLogger(__name__)


def _get_remote_auth_provider() -> AuthProvider:
    """Create a RemoteAuthProvider with JWTVerifier for JWT-only validation."""
    from fastmcp.server.auth import RemoteAuthProvider
    from fastmcp.server.auth.providers.jwt import JWTVerifier
    from pydantic import AnyHttpUrl

    settings = ch_mcp.settings.get_settings()
    auth0 = settings.auth0
    assert isinstance(auth0, ch_mcp.settings.RemoteAuth0Settings)
    domain = auth0.domain

    # NOTE: required_scopes is intentionally omitted here. Scope enforcement
    # is handled per-tool by AuthMiddleware + restrict_tag in server/__init__.py.
    # Setting required_scopes on JWTVerifier would reject tokens globally
    # (even for initialize/tools/list) before the middleware gets a chance to
    # apply per-tool checks.
    jwt_verifier = JWTVerifier(
        jwks_uri=f"https://{domain}/.well-known/jwks.json",
        issuer=f"https://{domain}/",
        audience=auth0.audience,
    )

    return RemoteAuthProvider(
        token_verifier=jwt_verifier,
        authorization_servers=[AnyHttpUrl(f"https://{domain}/")],
        base_url=settings.get_base_url(),
        scopes_supported=[scopes.CH_API_RO],
        resource_name="FCA Financial Services Register MCP",
    )


def _get_proxy_auth_provider(auth0: ch_mcp.settings.ProxyAuth0Settings) -> AuthProvider:
    """Create an Auth0Provider (OIDCProxy) for full OAuth proxy mode."""
    from cryptography.fernet import Fernet
    from fastmcp.server.auth.providers.auth0 import Auth0Provider
    from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

    import ch_mcp.azure.api
    import ch_mcp.azure.blob_key_value

    settings = ch_mcp.settings.get_settings()
    tmp_api = ch_mcp.azure.api.AzureAPI(settings.azure)

    return Auth0Provider(
        audience=auth0.audience,
        client_id=auth0.client_id,
        client_secret=auth0.client_secret,
        jwt_signing_key=auth0.jwt_signing_key,
        base_url=settings.get_base_url(),
        config_url=f"https://{auth0.domain}/.well-known/openid-configuration",
        required_scopes=[scopes.CH_API_RO],
        client_storage=FernetEncryptionWrapper(
            key_value=ch_mcp.azure.blob_key_value.AzureBlobStore(
                client=tmp_api.blob_service_client,
                container_name=settings.blob_store_names.auth0_clients,
                default_collection="auth0_clients",
            ),
            fernet=Fernet(auth0.storage_encryption_key),
        ),
    )


def get_auth_provider() -> AuthProvider|None:
    """Get the authentication provider based on configured auth mode."""
    settings = ch_mcp.settings.get_settings()

    if isinstance(settings.auth0, ch_mcp.settings.NoneAuth0Settings):
        logger.info("Authentication disabled (auth_mode=none)")
        return None

    if isinstance(settings.auth0, ch_mcp.settings.RemoteAuth0Settings):
        logger.info("Using RemoteAuthProvider (JWT verification only)")
        return _get_remote_auth_provider()

    logger.info("Using Auth0Provider (OAuth proxy mode)")
    return _get_proxy_auth_provider(settings.auth0)
