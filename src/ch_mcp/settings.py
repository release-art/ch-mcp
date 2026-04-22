"""Global settings for the ch-mcp project."""

from __future__ import annotations

import base64
import enum
import functools
import logging
import os
import re
from typing import Annotated, Any, Literal, Union

from pydantic import Field, GetCoreSchemaHandler, HttpUrl, field_validator, model_validator
from pydantic_core import core_schema
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_AZURE_TABLE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{2,62}$")


class AzureTableName(str):
    """Validated Azure Table Storage table name.

    Must be 3-63 alphanumeric characters starting with a letter.
    Hyphens, underscores, and other symbols are not permitted by Azure.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(cls, v: object) -> AzureTableName:
        if not isinstance(v, str):
            raise ValueError(f"Expected str, got {type(v).__name__}")
        if not _AZURE_TABLE_NAME_RE.match(v):
            raise ValueError(
                f"'{v}' is not a valid Azure Table Storage name. "
                "Must be 3-63 alphanumeric characters starting with a letter (no hyphens or other symbols)."
            )
        return cls(v)


@enum.unique
class AuthMode(enum.StrEnum):
    """Authentication mode selection."""

    REMOTE = "remote"
    PROXY = "proxy"


@enum.unique
class AzureCredentialType(enum.StrEnum):
    """Types of Azure credentials supported for authentication."""

    NONE = "none"
    DEFAULT = "default"


class AzureSettings(BaseSettings):
    """Azure storage configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="AZURE_",
        extra="forbid",
    )

    credential: Annotated[
        AzureCredentialType,
        Field(
            default=AzureCredentialType.DEFAULT,
            description="Azure credential type to use for authentication",
        ),
    ]

    storage_connection_string: Annotated[
        str | None,
        Field(
            default=None,
            description="Azure Storage connection string (required for NONE credential type)",
        ),
    ]

    storage_account: Annotated[
        str | None,
        Field(
            default=None,
            description="Azure Storage account name (required for DEFAULT credential type)",
        ),
    ]

    storage_blob_endpoint: Annotated[
        str | None,
        Field(
            default=None,
            description="Azure Blob Storage endpoint URL (optional, defaults to https://{account}.blob.core.windows.net)",
        ),
    ]

    storage_queue_endpoint: Annotated[
        str | None,
        Field(
            default=None,
            description="Azure Queue Storage endpoint URL (optional, defaults to https://{account}.queue.core.windows.net)",
        ),
    ]

    storage_table_endpoint: Annotated[
        str | None,
        Field(
            default=None,
            description="Azure Table Storage endpoint URL (optional, defaults to https://{account}.table.core.windows.net)",
        ),
    ]


class BlobStoreNamesSettings(BaseSettings):
    """Names of Azure Blob Storage containers used by the application.

    Each field maps to the container name for a specific internal store,
    configurable via the ``BLOB_STORE_NAME_*`` environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="BLOB_STORE_NAME_",
        extra="forbid",
    )

    auth0_clients: Annotated[
        str,
        Field(
            default="auth0-clients",
            description="Container name for the Auth0 OAuth client registration store (proxy mode).",
        ),
    ]


class TableStoreNamesSettings(BaseSettings):
    """Names of Azure Table Storage tables used by the application.

    Each field maps to a table name **prefix** for a specific internal store,
    configurable via the ``TABLE_STORE_NAME_*`` environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="TABLE_STORE_NAME_",
        extra="forbid",
    )

    api_cache: Annotated[
        AzureTableName,
        Field(
            default="apicache",
            description=(
                "Prefix for the API response cache table. The active table is named "
                "'{prefix}{cache_version_slug}', e.g. 'apicache00'. "
                "Bump __version__.cache_version to invalidate all cached entries on significant API changes; "
                "stale tables are deleted on startup and surviving entries expire via their TTL."
            ),
        ),
    ]


class CacheSettings(BaseSettings):
    """API response cache configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        extra="forbid",
    )

    ttl_seconds: Annotated[
        int,
        Field(
            default=86400,
            gt=0,
            description="API response cache TTL in seconds (default: 86400 = 24 hours).",
        ),
    ]


class _BaseAuth0Settings(BaseSettings):
    """Common Auth0 settings shared by all auth modes."""

    model_config = SettingsConfigDict(
        env_prefix="AUTH0_",
        extra="ignore",
    )

    domain: Annotated[
        str,
        Field(
            ...,
            description="Auth0 domain (e.g., 'your-tenant.auth0.com')",
        ),
    ]
    audience: Annotated[
        str,
        Field(
            ...,
            description="Auth0 API audience identifier",
        ),
    ]
    interactive_client_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Auth0 SPA client ID for the interactive web UI",
        ),
    ]


class RemoteAuth0Settings(_BaseAuth0Settings):
    """Auth0 settings for remote/JWT-only verification mode."""

    mode: Literal[AuthMode.REMOTE] = AuthMode.REMOTE


class ProxyAuth0Settings(_BaseAuth0Settings):
    """Auth0 settings for full OAuth proxy mode."""

    mode: Literal[AuthMode.PROXY]
    client_id: Annotated[
        str,
        Field(
            ...,
            description="Auth0 client ID",
        ),
    ]
    client_secret: Annotated[
        str,
        Field(
            ...,
            description="Auth0 client secret",
        ),
    ]
    jwt_signing_key: Annotated[
        str,
        Field(
            ...,
            description="JWT signing key for proxy mode token issuance",
        ),
    ]
    storage_encryption_key: Annotated[
        str,
        Field(
            ...,
            description="Encryption key for client token storage",
        ),
    ]

    @field_validator("storage_encryption_key")
    @classmethod
    def validate_storage_encryption_key(cls, v: str) -> str:
        """Validate that storage_encryption_key is 32 url-safe base64-encoded bytes."""
        try:
            decoded = base64.urlsafe_b64decode(v)
            if len(decoded) != 32:
                raise ValueError(f"must be 32 bytes when decoded, got {len(decoded)} bytes")
        except Exception as e:
            raise ValueError(f"must be 32 url-safe base64-encoded bytes: {e}") from e
        return v


Auth0Settings = Annotated[
    Union[RemoteAuth0Settings, ProxyAuth0Settings],
    Field(discriminator="mode"),
]


class ChApiSettings(BaseSettings):
    """Companies House API credentials and configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CH_API_",
        extra="forbid",
    )

    api_key: Annotated[
        str,
        Field(
            ...,
            description="Companies House API key (obtain from https://developer.company-information.service.gov.uk/)",
        ),
    ]
    use_sandbox: Annotated[
        bool,
        Field(
            default=False,
            description="Use the Companies House sandbox environment instead of the live API",
        ),
    ]
    base_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            description="Companies House API base URL (optional override; takes precedence over use_sandbox)",
        ),
    ]
    timeout: Annotated[
        float,
        Field(
            default=30.0,
            gt=0,
            description="API request timeout in seconds",
        ),
    ]
    max_retries: Annotated[
        int,
        Field(
            default=3,
            ge=0,
            description="Maximum number of retries for failed requests",
        ),
    ]


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="SERVER_",
        extra="forbid",
    )

    host: Annotated[
        str,
        Field(
            default="0.0.0.0",
            description="Server host address",
        ),
    ]
    port: Annotated[
        int,
        Field(
            default=8000,
            ge=1,
            le=65535,
            description="Server port number",
        ),
    ]
    base_url: Annotated[
        HttpUrl,
        Field(
            ...,
            description="Full base URL",
        ),
    ]
    workers: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            description="Number of worker processes",
        ),
    ]
    jwt_secret_key: Annotated[
        str,
        Field(
            description="Secret key for signing JWTs (if applicable)",
        ),
    ]


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="forbid",
    )

    level: Annotated[
        Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        Field(
            default="INFO",
            description="Logging level",
        ),
    ]
    format: Annotated[
        Literal["json", "text"],
        Field(
            default="text",
            description="Log output format",
        ),
    ]
    file: Annotated[
        str | None,
        Field(
            default=None,
            description="Log file path (None = stdout only)",
        ),
    ]


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        extra="forbid",
        case_sensitive=False,
    )

    # Environment and deployment
    environment: Annotated[
        Literal["development", "staging", "production"],
        Field(
            default="development",
            description="Application environment",
        ),
    ]
    debug: Annotated[
        bool,
        Field(
            default=False,
            description="Enable debug mode",
        ),
    ]

    # Nested settings
    azure: Annotated[AzureSettings, Field(default_factory=lambda: AzureSettings())]  # type: ignore[call-arg]
    blob_store_names: Annotated[BlobStoreNamesSettings, Field(default_factory=lambda: BlobStoreNamesSettings())]  # type: ignore[call-arg]
    table_store_names: Annotated[TableStoreNamesSettings, Field(default_factory=lambda: TableStoreNamesSettings())]  # type: ignore[call-arg]
    cache: Annotated[CacheSettings, Field(default_factory=lambda: CacheSettings())]  # type: ignore[call-arg]
    auth0: Auth0Settings
    ch_api: Annotated[ChApiSettings, Field(default_factory=lambda: ChApiSettings())]  # type: ignore[call-arg]

    @model_validator(mode="before")
    @classmethod
    def _build_auth0(cls, data: Any) -> Any:
        if isinstance(data, dict) and "auth0" not in data:
            mode = os.environ.get("AUTH0_MODE", AuthMode.REMOTE)
            data["auth0"] = ProxyAuth0Settings() if mode == AuthMode.PROXY else RemoteAuth0Settings()  # type: ignore[call-arg]
        return data

    server: Annotated[ServerSettings, Field(default_factory=lambda: ServerSettings())]  # type: ignore[call-arg]
    logging: Annotated[LoggingSettings, Field(default_factory=lambda: LoggingSettings())]  # type: ignore[call-arg]

    # Additional top-level settings
    cors_origins: Annotated[
        list[str],
        Field(
            default_factory=lambda: ["*"],
            description="Allowed CORS origins",
        ),
    ]
    api_version: Annotated[
        str,
        Field(
            default="v1",
            description="API version prefix",
        ),
    ]

    def get_base_url(self) -> str:
        """Get the full base URL for the application."""
        return str(self.server.base_url).rstrip("/")


@functools.lru_cache
def get_settings() -> Settings:
    """
    Get cached global settings instance.

    This function is cached to ensure a single Settings instance
    is used throughout the application lifecycle.

    Returns:
        Settings: The global settings instance
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        logger.error(
            "Failed to construct Settings. Environment variables:",
            extra={"environ": dict(os.environ)},
        )
        raise
