[![Release](https://github.com/release-art/ch-mcp/actions/workflows/release.yml/badge.svg)](https://github.com/release-art/ch-mcp/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/companies-house-mcp?logo=python&color=41bb13)](https://pypi.org/project/companies-house-mcp)

# Companies House MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes the UK [Companies House register](https://find-and-update.company-information.service.gov.uk/) to LLM clients as a set of read-only tools. Built on [FastMCP v3](https://gofastmcp.com/) and the [`ch-api`](https://github.com/release-art/ch-api) async client.

## Overview

- **22 read-only tools** across five domains: search, companies, officers, PSCs (persons with significant control), and filings.
- **Two transports**: HTTP (Starlette/uvicorn) for remote MCP clients, and stdio for local integrations.
- **OAuth2 via Auth0**, with three modes:
  - `none` — no authentication (local dev / trusted-ingress only).
  - `remote` — JWT verification only (the MCP server trusts an upstream Auth0 tenant).
  - `proxy` — full OAuth proxy with dynamic client registration; tokens are persisted to Azure Blob Storage, encrypted with Fernet.
- **Scope-based authorization**: tools tagged `ch_api:read` require the `ch-api:read` scope in the access token. Enforcement is per-tool, so `initialize` and `tools/list` remain reachable by unauthenticated clients.
- **Structured responses**: Pydantic models synthesised by reflection from `ch-api` types. Every response carries a typed `refs` sub-object holding the resource IDs (company number, charge id, document id, …) extracted from the upstream `links` block — chain tool calls by feeding those IDs straight into the next tool's input.

## Tools

| Module | Tools |
|--------|-------|
| [`search.py`](src/ch_mcp/server/search.py) | `search_companies`, `search_officers`, `search_disqualified_officers`, `alphabetical_companies_search`, `search_dissolved_companies`, `advanced_company_search` |
| [`companies.py`](src/ch_mcp/server/companies.py) | `get_company_profile`, `get_company_registers`, `get_company_uk_establishments` |
| [`officers.py`](src/ch_mcp/server/officers.py) | `get_officer_list`, `get_officer_appointments`, `get_officer_disqualification` |
| [`psc.py`](src/ch_mcp/server/psc.py) | `get_company_psc_list`, `get_company_psc_statements`, `get_company_psc` |
| [`filings.py`](src/ch_mcp/server/filings.py) | `get_company_charges`, `get_company_charge_details`, `get_company_filing_history`, `get_company_insolvency`, `get_company_exemptions`, `get_document_metadata`, `get_document_content` |

All tools are decorated with `ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)`.

### Discriminated tools

Two tools dispatch across several underlying Companies House endpoints via a
required ``kind`` parameter:

- **`get_company_psc`** — one of eight PSC variants (individual / corporate
  entity / legal person / super-secure, each with a beneficial-owner
  counterpart). Copy the ``kind`` straight from the corresponding
  `get_company_psc_list` item.
- **`get_officer_disqualification`** — ``natural-disqualification`` (human
  director) or ``corporate-disqualification`` (company acting as director).
  Determined from `search_disqualified_officers` results.

Both return a pydantic discriminated union keyed on the same ``kind`` field so
MCP clients can statically narrow the response to the correct variant.

### Response `refs` — chaining tool calls

Every reflected response carries a typed `refs` sub-object with the IDs that
`ch_api`'s `links` block encodes as URL path segments. The contents depend on
the response type:

- `CompanyProfile.refs.company_number`
- `FilingHistoryItem.refs.transaction_id`, `refs.document_id` (when the
  filing has a downloadable document)
- `ChargeDetails.refs.charge_id`
- PSC list/record items carry `refs.psc_id`
- Disqualification records carry `refs.officer_id`
- `DocumentMetadata.refs.document_id`

Copy those IDs directly into the matching `*Param` on the next tool call —
they are the exact string shape the tool accepts. The raw `links` URLs are
stripped from the response to keep it compact and to make the chain
explicit.

### Document downloads

`get_company_filing_history` items may carry `refs.document_id`. Pass it to
`get_document_metadata` to see which content types are available (PDF,
JSON, XML, XHTML, ZIP, CSV), then to `get_document_content` to receive a
**download URL** — the tool doesn't transfer bytes through MCP, it hands
back a short-lived HTTP link that, when fetched, streams the raw document
with the correct `Content-Type`. No base64 inflation, no MCP-client binary-
rendering dependency, no 10 MiB response cap.

The URL's backend depends on the transport:

- **HTTP transport** (default deployment): the URL points at this server's
  own `/documents/{signed_token}` route, signed with
  `SERVER_JWT_SECRET_KEY`, valid for ~10 minutes. The route streams from a
  permanent Azure Blob cache (container name
  `BLOB_STORE_NAME_DOCUMENT_CONTENT`, default `document-content`), fetching
  from Companies House on cache miss. Because documents are immutable,
  entries never expire — re-minting a URL on TTL expiry is free.
- **stdio transport**: the URL is the Companies House-issued pre-signed
  S3 link, valid for ~60 seconds. Fetch immediately.

Size guardrail (`CACHE_MAX_DOCUMENT_BYTES`, default 10 MiB) is enforced by
the HTTP route; a 413 is returned for oversize filings.

### Intentionally omitted endpoints

Three Companies House endpoints are deliberately **not** surfaced as MCP tools
because their response is a strict subset of data already available via another
tool. Omitting them keeps the total tool count down (better model-selection
accuracy) without losing any retrievable field.

| Upstream endpoint | Supplied by instead | Notes |
|---|---|---|
| `GET /company/{number}/registered-office-address` | `get_company_profile` | The profile's `registered_office_address` sub-field is a **superset**: it additionally exposes `care_of` and `po_box`. The standalone endpoint's unique fields are `etag`, `kind`, `links` (stripped by the LinksSection exclusion) and `accept_appropriate_office_address_statement` (a write-only PUT flag irrelevant to a read-only client). |
| `GET /company/{number}/filing-history/{id}` | `get_company_filing_history` | Both endpoints deserialise into the same `FilingHistoryItem` pydantic class — field set is identical. |
| `GET /company/{number}/appointments/{appointment_id}` | `get_officer_list` | Both endpoints deserialise into the same `OfficerSummary` pydantic class — field set is identical. |

If a new CH API version ever changes these endpoints so the single-item call
returns richer data than the collection item, these tools should be restored.

## Quick start

### Prerequisites

- Python **3.13+**
- [PDM](https://pdm-project.org/) for dependency management
- Companies House API key — register at <https://developer.company-information.service.gov.uk/>
- An Auth0 tenant (only the `remote` mode needs a tenant at minimum; `proxy` mode additionally needs client credentials and Azure Blob Storage)

### Install

```bash
pdm install
cp .env.example .env
# edit .env with your credentials
```

### Run the HTTP server

```bash
pdm run python -m ch_mcp serve                 # production-like
pdm run python -m ch_mcp serve --reload        # with autoreload
```

By default the server binds `0.0.0.0:8000`. `SERVER_BASE_URL` must be set (used for OAuth metadata and resource URLs).

### Run over stdio

```bash
pdm run python -m ch_mcp stdio
```

`stdio` mode skips the `AuthMiddleware` entirely — see [`server/__init__.py`](src/ch_mcp/server/__init__.py).

### Docker

```bash
docker-compose up --build
```

`docker-compose.yml` launches the server alongside an [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) emulator. Set `CH_API_API_KEY`, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, and `SERVER_BASE_URL` in the environment of the host running `docker-compose`.

### Sandbox

Set `CH_API_USE_SANDBOX=true` to point the underlying client at the [Companies House sandbox](https://developer-specs.company-information.service.gov.uk/) instead of the live API. Use a sandbox API key with it.

## Architecture

```
LLM client
  │  MCP over HTTP (OAuth2 Bearer) or stdio
  ▼
┌─────────────────────────────────────────────┐
│ FastMCP server (ch_mcp.server.get_server)   │
│ ─────────────────────────────────────────── │
│  Middleware stack (outer → inner):          │
│    ErrorHandlingMiddleware                  │
│    RateLimitingMiddleware                   │
│    LoggingMiddleware                        │
│    AuthMiddleware (restrict_tag CH_API_RO)  │
│    ChCachingMiddleware                      │
│ ─────────────────────────────────────────── │
│  Sub-servers (mounted):                     │
│    search · companies · officers ·          │
│    psc · filings                            │
│ ─────────────────────────────────────────── │
│  Auth provider:                             │
│    RemoteAuthProvider  (mode=remote)        │
│    Auth0Provider       (mode=proxy)         │
└───────────────────────┬─────────────────────┘
                        ▼
                   ch_api.Client
                        ▼
           Companies House REST API
```

### Dependency injection

Tools receive the shared `ch_api` client through FastMCP's `Depends` chain defined in [`server/deps.py`](src/ch_mcp/server/deps.py):

```python
async def get_company_profile(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyProfile | None:
    result = await ch_client.get_company_profile(company_number)
    if result is None:
        return None
    return types.company.CompanyProfile.from_api_t(result)
```

The client is constructed once in the server lifespan and reused across requests.

### Type reflection

Response types are synthesised from `ch-api` types by `reflect_ch_api_t()` in [`server/types/base.py`](src/ch_mcp/server/types/base.py). The raw `links` HATEOAS block is replaced with a typed `refs` sub-object (see [`server/types/refs.py`](src/ch_mcp/server/types/refs.py)) whose fields hold the IDs extracted from the link URLs — `company_number`, `charge_id`, `document_id`, etc. — in exactly the string shape the corresponding `*Param` inputs expect. `etag` fields (optimistic-concurrency tokens used only by write endpoints) are also stripped. Tools convert raw results with `Model.from_api_t(api_result)`.

### Auth: scopes vs tags

Note the hyphen-vs-underscore distinction:

- **Scope** ([`auth/scopes.py`](src/ch_mcp/server/auth/scopes.py)): `CH_API_RO = "ch-api:read"` — the OAuth scope claimed in access tokens.
- **Tag** ([`auth/tags.py`](src/ch_mcp/server/auth/tags.py)): `CH_API_RO = "ch_api:read"` — the tag applied to tool decorators.

`AuthMiddleware` calls `restrict_tag(CH_API_RO, scopes=[CH_API_RO])` — any tool tagged with `ch_api:read` requires the `ch-api:read` scope to execute. Every tool in every sub-server is tagged, so in practice every tool call requires the scope. `initialize` and `tools/list` remain reachable without it. On `stdio`, the middleware short-circuits.

## Configuration

All settings are loaded from environment variables via Pydantic-Settings. See [SETTINGS.md](SETTINGS.md) for the full reference.

The most important variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `CH_API_API_KEY` | Yes | Companies House API key |
| `CH_API_USE_SANDBOX` | No (default `false`) | Use the CH sandbox environment |
| `AUTH0_MODE` | No (`remote` default) | `none`, `remote`, or `proxy` |
| `AUTH0_DOMAIN` / `AUTH0_AUDIENCE` | `remote`/`proxy` only | Auth0 tenant identifiers |
| `AUTH0_CLIENT_ID` / `AUTH0_CLIENT_SECRET` / `AUTH0_JWT_SIGNING_KEY` / `AUTH0_STORAGE_ENCRYPTION_KEY` | `proxy` mode only | OAuth proxy secrets |
| `SERVER_HTTP_RESOURCES_DIR` | No | Path for the HTML template(s) behind the `GET /` landing page. Defaults to the in-package directory. |
| `AZURE_CREDENTIAL` | `proxy` mode | `none` (connection string / Azurite) or `default` (DefaultAzureCredential) |
| `AZURE_STORAGE_CONNECTION_STRING` | When `AZURE_CREDENTIAL=none` | Connection string for Azurite or an Azure Storage account |
| `AZURE_STORAGE_ACCOUNT` | When `AZURE_CREDENTIAL=default` | Storage account name |
| `SERVER_BASE_URL` | Yes | Public base URL used in OAuth resource metadata |

## Health check

The HTTP app exposes `GET /.container/health`, returning service name, version, uptime, and timestamp. The Dockerfile `HEALTHCHECK` polls this endpoint.

## Development

```bash
pdm run pytest                                         # all tests with coverage
pdm run pytest tests/server/test_company_simple.py    # single file
pdm run pytest tests/server/test_company_simple.py::test_get_company_profile -v

pdm run ruff check                                     # lint
pdm run ruff check --fix                               # auto-fix
pdm run ruff format                                    # format
```

Tests use FastMCP's in-memory `FastMCPTransport` — no HTTP server or live Auth0/Azure is required. Fixtures in [`tests/server/conftest.py`](tests/server/conftest.py) replace the `ch-api` client with a record/replay mock (see [`tests/test_plugins/mock_client/mock_ch_api.py`](tests/test_plugins/mock_client/mock_ch_api.py)) and substitute a synthetic `AccessToken` so the auth middleware runs without live tokens. To test scope denial, override the `oauth_scopes` fixture to return `[]`.

**First run populates the cache.** On first run, set `CH_API_API_KEY=<real-key>` in the environment; the mock will hit the live Companies House API on cache miss and persist responses under `tests/mock_ch_api_cache/`. Commit those files so subsequent runs execute fully offline.

### Code style

- Line length: 120
- Ruff rules: `A`, `B`, `C`, `E`, `F`, `I`, `W`, `N`, `C4`, `T20`, `PTH`
- Python 3.13+

## Project layout

```
src/ch_mcp/
├── __main__.py              # python -m ch_mcp → CLI
├── cli.py                   # typer CLI (serve / stdio)
├── settings.py              # Pydantic-Settings config
├── logging.py               # dictConfig-based logging setup
├── uvcorn_app.py            # Starlette/uvicorn HTTP app factory
├── azure/                   # Azure Blob key-value store + client factory
├── http/                    # Interactive OAuth UI routes + static assets
└── server/
    ├── __init__.py          # get_server(): mounts sub-servers + middleware
    ├── app.py               # ChApp lifespan container
    ├── deps.py              # FastMCP Depends wiring
    ├── search.py            # Companies House search tools
    ├── companies.py         # Company profile / registers / UK establishments
    ├── officers.py          # Officer list + appointments + disqualifications
    ├── psc.py               # Persons with significant control
    ├── filings.py           # Charges, filing history, insolvency, exemptions
    ├── auth/                # Auth provider, scopes, tags
    └── types/               # Reflected Pydantic models
```

## License

MIT — see [LICENSE](LICENSE).

## Related

- [ch-api](https://github.com/release-art/ch-api) — the underlying Companies House REST client.
- [FastMCP](https://gofastmcp.com/) — MCP server framework.
- [Companies House developer hub](https://developer.company-information.service.gov.uk/) — upstream API.
