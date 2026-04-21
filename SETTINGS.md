# Settings Reference

Configuration for the FCA MCP server, built on [Pydantic v2](https://docs.pydantic.dev/) and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). All values are loaded from environment variables (or a `.env` file); extra variables are rejected (`extra="forbid"`).

Source of truth: [`src/fca_mcp/settings.py`](src/fca_mcp/settings.py).

## Quick start

```bash
cp .env.example .env
# edit .env with your values
```

```python
from fca_mcp.settings import get_settings

settings = get_settings()          # cached singleton via @functools.lru_cache
settings.auth0.domain
settings.fca_api.username
settings.server.base_url
```

`get_settings()` raises a `pydantic.ValidationError` on startup if any required variable is missing or malformed.

## Top-level `Settings`

| Field | Env var | Type | Default | Notes |
|-------|---------|------|---------|-------|
| `environment` | `ENVIRONMENT` | `development` \| `staging` \| `production` | `development` | |
| `debug` | `DEBUG` | `bool` | `False` | |
| `cors_origins` | `CORS_ORIGINS` | `list[str]` | `["*"]` | |
| `api_version` | `API_VERSION` | `str` | `"v1"` | |
| `azure` | `AZURE_*` | `AzureSettings` | (factory) | |
| `blob_store_names` | `BLOB_STORE_NAME_*` | `BlobStoreNamesSettings` | (factory) | Blob container names per internal store. |
| `auth0` | `AUTH0_*` | `RemoteAuth0Settings` \| `ProxyAuth0Settings` | mode selected via `AUTH0_MODE` | |
| `fca_api` | `FCA_API_*` | `FcaApiSettings` | (factory) | |
| `server` | `SERVER_*` | `ServerSettings` | (factory) | |
| `logging` | `LOG_*` | `LoggingSettings` | (factory) | |

## `auth0` — Auth0 settings

The `auth0` block is a tagged union discriminated by `mode`. Choose the mode by setting `AUTH0_MODE`:

- `remote` (default) — the MCP server only **verifies** access tokens issued by an upstream Auth0 tenant. No client registration, no token storage.
- `proxy` — the MCP server runs a full OAuth proxy via `fastmcp`'s `Auth0Provider`, persists client registrations in Azure Blob Storage (Fernet-encrypted), and issues its own tokens signed with `AUTH0_JWT_SIGNING_KEY`.

### Shared (both modes)

| Env var | Required | Description |
|---------|----------|-------------|
| `AUTH0_MODE` | No (default `remote`) | `remote` or `proxy`. |
| `AUTH0_DOMAIN` | Yes | e.g. `tenant.auth0.com`. |
| `AUTH0_AUDIENCE` | Yes | API identifier configured in Auth0. |
| `AUTH0_INTERACTIVE_CLIENT_ID` | No | SPA client ID that enables the `/interactive` web UI. When unset, interactive routes are not mounted. |

### Proxy mode only

| Env var | Required | Description |
|---------|----------|-------------|
| `AUTH0_CLIENT_ID` | Yes | Auth0 application client ID. |
| `AUTH0_CLIENT_SECRET` | Yes | Auth0 application client secret. |
| `AUTH0_JWT_SIGNING_KEY` | Yes | Key used to sign tokens issued by the proxy. |
| `AUTH0_STORAGE_ENCRYPTION_KEY` | Yes | 32 bytes, url-safe base64 encoded. Fernet key used to encrypt client records in Azure Blob. |

`AUTH0_STORAGE_ENCRYPTION_KEY` is validated on startup: it must base64-decode to exactly 32 bytes.

## `azure` — Azure storage (used in proxy mode)

| Env var | Type | Default | Description |
|---------|------|---------|-------------|
| `AZURE_CREDENTIAL` | `none` \| `default` | `default` | `none` uses a connection string (Azurite/dev); `default` uses `DefaultAzureCredential` (managed identity, Azure CLI, etc.). |
| `AZURE_STORAGE_CONNECTION_STRING` | `str` | — | Required when `AZURE_CREDENTIAL=none`. |
| `AZURE_STORAGE_ACCOUNT` | `str` | — | Required when `AZURE_CREDENTIAL=default`. |
| `AZURE_STORAGE_BLOB_ENDPOINT` | `str` | `https://{account}.blob.core.windows.net` | Optional override. |
| `AZURE_STORAGE_QUEUE_ENDPOINT` | `str` | `https://{account}.queue.core.windows.net` | Optional override. |
| `AZURE_STORAGE_TABLE_ENDPOINT` | `str` | `https://{account}.table.core.windows.net` | Optional override. |

Only the blob endpoint is used today (for OAuth client storage); the queue/table endpoints exist for future extension.

## `blob_store_names` — Azure Blob container names

Names of the Azure Blob Storage containers the application provisions/uses. Override any of these to match your environment's naming conventions.

| Env var | Type | Default | Description |
|---------|------|---------|-------------|
| `BLOB_STORE_NAME_AUTH0_CLIENTS` | `str` | `auth0-clients` | Container for OAuth client registrations in `AUTH0_MODE=proxy`. |

Local development with Azurite:

```bash
AZURE_CREDENTIAL=none
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=...;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
```

Production with managed identity:

```bash
AZURE_CREDENTIAL=default
AZURE_STORAGE_ACCOUNT=mycompanystorage
```

## `fca_api` — FCA Register credentials

| Env var | Type | Default | Description |
|---------|------|---------|-------------|
| `FCA_API_USERNAME` | `str` | — (required) | FCA Register email. |
| `FCA_API_KEY` | `str` | — (required) | FCA Register API key. |
| `FCA_API_BASE_URL` | `HttpUrl` | unset | Optional override. |
| `FCA_API_TIMEOUT` | `float > 0` | `30.0` | Request timeout, seconds. |
| `FCA_API_MAX_RETRIES` | `int >= 0` | `3` | Retry count for transient failures. |

## `server` — HTTP server

| Env var | Type | Default | Description |
|---------|------|---------|-------------|
| `SERVER_HOST` | `str` | `0.0.0.0` | Bind address. |
| `SERVER_PORT` | `int` (1–65535) | `8000` | Bind port. |
| `SERVER_BASE_URL` | `HttpUrl` | — (required) | Public base URL exposed in OAuth resource metadata. |
| `SERVER_WORKERS` | `int >= 1` | `1` | Uvicorn worker count. |

`SERVER_BASE_URL` is required because `RemoteAuthProvider` / `Auth0Provider` include it in the OAuth protected resource metadata. Use `http://localhost:8000` locally.

The `--reload` flag on `python -m fca_mcp serve` is passed through to uvicorn directly and is independent of this settings block.

## `logging`

| Env var | Type | Default | Description |
|---------|------|---------|-------------|
| `LOG_LEVEL` | `DEBUG`\|`INFO`\|`WARNING`\|`ERROR`\|`CRITICAL` | `INFO` | |
| `LOG_FORMAT` | `text` \| `json` | `text` | |
| `LOG_FILE` | `str` | unset | When set, log to file in addition to stdout. |

Runtime logging config is assembled by [`fca_mcp.logging.get_config()`](src/fca_mcp/logging.py).

## Usage patterns

### FastAPI / FastMCP dependency injection

```python
from typing import Annotated
from fastapi import Depends
from fca_mcp.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]

async def handler(settings: SettingsDep):
    return {"env": settings.environment}
```

### Resolving the public base URL

```python
settings = get_settings()
base_url = settings.get_base_url()   # str(settings.server.base_url).rstrip("/")
```

### Environment-specific branches

```python
if settings.environment == "production":
    ...
elif settings.debug:
    ...
```

## Troubleshooting

### Missing required variable

```
pydantic.ValidationError: 1 validation error for Settings
server.base_url
  Field required
```

Set the variable named in the error (here `SERVER_BASE_URL`) and restart.

### Bad `AUTH0_STORAGE_ENCRYPTION_KEY`

```
ValueError: must be 32 url-safe base64-encoded bytes
```

Generate one with:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Unexpected variable rejected

`extra="forbid"` means unknown variables under a prefix fail validation. Remove the stray variable, or move it to its correct prefix.

## Best practices

- Always go through `get_settings()`. Don't instantiate `Settings()` directly — you lose the cache and skip validation aggregation.
- Never commit `.env`. Use `.env.example` as the template.
- Call `get_settings()` at startup (the lifespan already does) so configuration errors surface immediately.
