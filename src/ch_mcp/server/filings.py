"""Companies House filings tools (charges, filing history, insolvency, exemptions)."""

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
            "Companies House charge identifier. Obtain from the ``id`` field of a"
            " ``get_company_charges`` item, or from the trailing path segment of"
            " the item's ``self`` link."
        ),
        min_length=1,
    ),
]

FilingHistoryIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Companies House filing history transaction identifier. Obtain from"
            " the ``transaction_id`` field of ``get_company_filing_history`` items."
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
    address changes, share capital changes, resolutions, and more. Each entry
    has a ``transaction_id`` that can be passed to ``get_filing_history_item``
    for any richer per-filing metadata.
    """
    out = await ch_client.get_company_filing_history(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.filings.FilingHistoryItem](
        items=[types.filings.FilingHistoryItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@filings_mcp.tool(**_TOOL_KW)
async def get_filing_history_item(
    company_number: CompanyNumberParam,
    filing_history_id: FilingHistoryIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.FilingHistoryItem | None:
    """Fetch a single filing history transaction by its transaction_id.

    Equivalent to finding the matching entry in ``get_company_filing_history``,
    but issued as a direct lookup. Use when you already have a specific
    transaction_id and want to refresh it without paging through the history.
    """
    result = await ch_client.get_filing_history_item(company_number, filing_history_id)
    if result is None:
        return None
    return types.filings.FilingHistoryItem.from_api_t(result)


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


def get_server() -> fastmcp.FastMCP:
    return filings_mcp
