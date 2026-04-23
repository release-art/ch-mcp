"""Companies House filings tools (charges, filing history, insolvency, exemptions, documents)."""

import logging
import os
from typing import Annotated

import ch_api
import ch_api.types.pagination.types as _ch_pagination
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

import ch_mcp

from . import auth, deps, document_url, types
from .companies import CompanyNumberParam

# Signed-URL TTL for the ch-mcp HTTP document-proxy route. The URL points at
# an endpoint we own, so the TTL only limits the link-leak window — the
# underlying bytes remain cached permanently in Azure Blob Storage, so
# regenerating the URL is always cheap.
_PROXY_URL_TTL_SECONDS = 600

logger = logging.getLogger(__name__)

ChargeIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Companies House charge identifier. Copy from the ``refs.charge_id``"
            " field of the matching ``get_company_charges`` item."
        ),
        min_length=1,
    ),
]

DocumentIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Companies House document identifier. Copy from the ``refs.document_id``"
            " field of a ``get_company_filing_history`` item. Only populated when"
            " the filing has a downloadable document attached."
        ),
        min_length=1,
    ),
]

# Intentionally a plain string, NOT a Literal. The Companies House API advertises
# six content types but is known to return others in the wild — a closed enum
# here would reject valid calls. The tool logs a warning for unknown values so
# we can track new ones without blocking the caller.
_ADVERTISED_DOCUMENT_CONTENT_TYPES: frozenset[str] = frozenset(
    (
        "application/pdf",
        "application/json",
        "application/xml",
        "application/xhtml+xml",
        "application/zip",
        "text/csv",
    )
)
DocumentContentTypeParam = Annotated[
    str,
    pydantic.Field(
        default="application/pdf",
        description=(
            "MIME type of the document representation to download. The Companies"
            " House API advertises: 'application/pdf', 'application/json',"
            " 'application/xml', 'application/xhtml+xml', 'application/zip',"
            " 'text/csv' — but any MIME string is accepted. Check a document's"
            " ``resources`` map (via ``get_document_metadata``) to see which"
            " types are actually available for that document before calling this."
            " Defaults to 'application/pdf'."
        ),
        min_length=1,
    ),
]

filings_mcp = fastmcp.FastMCP("filings", on_duplicate="error")

_TOOL_KW = {
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    "tags": {auth.tags.CH_API_RO},
}

_NextPageParam = Annotated[
    _ch_pagination.NextPageToken | None,
    pydantic.Field(
        default=None,
        description=(
            "Opaque cursor from a previous page's pagination.next_page. Omit on the"
            " first call; pass the previous response's token to fetch the next page."
        ),
    ),
]


@filings_mcp.tool(**_TOOL_KW)
async def get_company_charges(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.ChargeList | None:
    """List all registered charges (security interests over assets) for a company.

    A charge is a form of security granted to a lender against company assets
    (mortgages, debentures, fixed/floating charges). Use when assessing the
    company's debt exposure or encumbrances. Returns ``None`` if the company has
    no charges recorded.
    """
    result = await ch_client.get_company_charges(company_number)
    if result is None:
        return None
    return types.filings.ChargeList.from_api_t(result)


@filings_mcp.tool(**_TOOL_KW)
async def get_company_charge_details(
    company_number: CompanyNumberParam,
    charge_id: ChargeIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.ChargeDetails | None:
    """Fetch full details of a single charge registered against a company.

    Returns the charge's classification, particulars, secured details, persons
    entitled, transactions (creation, amendment, satisfaction), and any
    associated insolvency cases. Use after ``get_company_charges`` with the
    ``charge_id`` of the item you want to inspect.
    """
    result = await ch_client.get_company_charge_details(company_number, charge_id)
    if result is None:
        return None
    return types.filings.ChargeDetails.from_api_t(result)


@filings_mcp.tool(**_TOOL_KW)
async def get_company_filing_history(
    company_number: CompanyNumberParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.filings.FilingHistoryItem]:
    """List a company's filing history — every document submitted to Companies House.

    Covers the full statutory history: incorporation, accounts, confirmation
    statements (formerly annual returns), officer appointments and resignations,
    address changes, share capital changes, resolutions, and more. Each entry's
    ``refs`` carries a ``transaction_id`` and, when a downloadable document is
    attached, a ``document_id`` that can be fed into ``get_document_metadata``
    and ``get_document_content``.
    """
    out = await ch_client.get_company_filing_history(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.filings.FilingHistoryItem](
        items=[types.filings.FilingHistoryItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@filings_mcp.tool(**_TOOL_KW)
async def get_company_insolvency(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.CompanyInsolvency | None:
    """Fetch insolvency proceedings (liquidation, administration, CVA, etc.) for a company.

    Returns ``None`` for the vast majority of companies. Populated when the
    company has been or is subject to formal insolvency: liquidation, receivership,
    administration, company voluntary arrangement, or similar proceedings. Contains
    case type, key dates, and appointed insolvency practitioners.
    """
    result = await ch_client.get_company_insolvency(company_number)
    if result is None:
        return None
    return types.filings.CompanyInsolvency.from_api_t(result)


@filings_mcp.tool(**_TOOL_KW)
async def get_company_exemptions(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.CompanyExemptions | None:
    """Fetch any exemptions granted to a company from certain filing requirements.

    Exemptions typically apply to PSC-register obligations for companies whose
    shares are admitted to trading on certain regulated markets, or to
    disclosure-and-transparency-rules exemptions. Returns ``None`` for companies
    without any recorded exemptions.
    """
    result = await ch_client.get_company_exemptions(company_number)
    if result is None:
        return None
    return types.filings.CompanyExemptions.from_api_t(result)


@filings_mcp.tool(**_TOOL_KW)
async def get_document_metadata(
    document_id: DocumentIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.DocumentMetadata | None:
    """Fetch metadata for a single filed document (PDF, JSON, XML, …).

    Returns the document's identifiers, page count, filename, filing category,
    and a ``resources`` map keyed by MIME type showing the content-length and
    timestamps for each representation the API can serve. Use the map to decide
    which ``content_type`` to request from ``get_document_content``. Returns
    ``None`` when the document is unknown.

    Typical chain: ``get_company_filing_history → refs.document_id →
    get_document_metadata → get_document_content``.
    """
    result = await ch_client.get_document_metadata(document_id)
    if result is None:
        return None
    return types.filings.DocumentMetadata.from_api_t(result)


@filings_mcp.tool(**_TOOL_KW)
async def get_document_content(
    document_id: DocumentIdParam,
    content_type: DocumentContentTypeParam = "application/pdf",
) -> types.filings.DocumentDownload:
    """Return a downloadable URL for a single filed Companies House document.

    The tool itself does not transfer bytes — it returns a short-lived HTTP
    URL (~10 minutes) pointing at this server's own
    ``/documents/{signed_token}`` route. Fetching the URL streams the raw
    document with the correct ``Content-Type``. This keeps responses
    lightweight and avoids base64 inflation through MCP. Typical chain:
    ``get_company_filing_history → refs.document_id → get_document_content →
    fetch url``.

    Behind the scenes the route reads bytes from a permanent Azure Blob
    cache (fetching from Companies House on the first miss, then serving
    every subsequent request for the same ``(document_id, content_type)``
    from cache). Because the bytes are cached permanently, regenerating an
    expired URL is always free.

    **Transport**: this tool only works in HTTP mode — it relies on this
    server exposing the ``/documents/{token}`` route. Calling it under
    stdio raises immediately with a clear error.

    **Errors.** Document-not-found and content-type-unavailable (HTTP 406)
    errors surface only when the URL is fetched, not when this tool is
    called. Call ``get_document_metadata`` first to check which content
    types a document actually publishes.
    """
    if os.environ.get("CH_MCP_TRANSPORT") == "stdio":
        raise RuntimeError(
            "get_document_content requires the HTTP transport. This server is running"
            " under stdio, where the /documents/{token} route is not mounted."
        )

    if content_type not in _ADVERTISED_DOCUMENT_CONTENT_TYPES:
        logger.warning(
            "get_document_content called with non-advertised content_type %r (document_id=%s). "
            "Passing through to the API; update _ADVERTISED_DOCUMENT_CONTENT_TYPES if this "
            "turns out to be a valid new type.",
            content_type,
            document_id,
        )

    settings = ch_mcp.settings.get_settings()
    token = document_url.mint_document_token(
        secret=settings.server.jwt_secret_key,
        document_id=document_id,
        content_type=content_type,
        ttl_seconds=_PROXY_URL_TTL_SECONDS,
    )
    base_url = str(settings.server.base_url).rstrip("/")
    return types.filings.DocumentDownload(
        document_id=document_id,
        content_type=content_type,
        url=f"{base_url}/documents/{token}",
        expires_in_seconds=_PROXY_URL_TTL_SECONDS,
    )


def get_server() -> fastmcp.FastMCP:
    return filings_mcp
