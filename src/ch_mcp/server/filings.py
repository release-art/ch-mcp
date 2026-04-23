"""Companies House filings tools (charges, filing history, insolvency, exemptions, documents)."""

import logging
from typing import Annotated

import ch_api
import ch_api.types.pagination.types as _ch_pagination
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

from . import auth, deps, types
from .companies import CompanyNumberParam

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
    and ``get_document_url``.
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
    which ``content_type`` to request from ``get_document_url``. Returns
    ``None`` when the document is unknown.

    Typical chain: ``get_company_filing_history → refs.document_id →
    get_document_metadata → get_document_url``.
    """
    result = await ch_client.get_document_metadata(document_id)
    if result is None:
        return None
    return types.filings.DocumentMetadata.from_api_t(result)


@filings_mcp.tool(**_TOOL_KW)
async def get_document_url(
    document_id: DocumentIdParam,
    content_type: DocumentContentTypeParam = "application/pdf",
    ch_client: ch_api.Client = deps.ChApiDep,
) -> str | None:
    """Return a pre-signed download URL for a single filed document.

    The URL is a short-lived redirect target issued by the Companies House
    Document API. **It expires after ~60 seconds** — fetch it immediately
    rather than persisting or passing it around. Returns ``None`` when the
    document is unknown. A 406 upstream response (the requested
    ``content_type`` is not available for this document) surfaces as an
    exception — call ``get_document_metadata`` first to see which types are
    actually available.
    """
    if content_type not in _ADVERTISED_DOCUMENT_CONTENT_TYPES:
        logger.warning(
            "get_document_url called with non-advertised content_type %r (document_id=%s). "
            "Passing through to the API; update _ADVERTISED_DOCUMENT_CONTENT_TYPES if this "
            "turns out to be a valid new type.",
            content_type,
            document_id,
        )
    return await ch_client.get_document_url(document_id, content_type=content_type)


def get_server() -> fastmcp.FastMCP:
    return filings_mcp
