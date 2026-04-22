"""Companies House filings-related tools (charges, filing history, insolvency, exemptions)."""

import logging
from typing import Annotated

import ch_api
import ch_api.types.pagination.types as _ch_pagination
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

from . import deps, types
from .companies import CompanyNumberParam

logger = logging.getLogger(__name__)

ChargeIdParam = Annotated[
    str,
    pydantic.Field(description="Identifier of a specific charge on a company, as returned by get_company_charges."),
]

FilingHistoryIdParam = Annotated[
    str,
    pydantic.Field(description="Filing history transaction ID, as returned by get_company_filing_history."),
]

filings_mcp = fastmcp.FastMCP("filings", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@filings_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_charges(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.ChargeList | None:
    """Retrieve all registered charges (security interests) on a company.

    Charges record borrowings secured against company assets. Use to assess the
    debt/security posture of a company.
    """
    result = await ch_client.get_company_charges(company_number)
    if result is None:
        return None
    return types.filings.ChargeList.from_api_t(result)


@filings_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_charge_details(
    company_number: CompanyNumberParam,
    charge_id: ChargeIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.ChargeDetails | None:
    """Retrieve full detail for a single charge on a company."""
    result = await ch_client.get_company_charge_details(company_number, charge_id)
    if result is None:
        return None
    return types.filings.ChargeDetails.from_api_t(result)


@filings_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_filing_history(
    company_number: CompanyNumberParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.filings.FilingHistoryItem]:
    """List a company's filing history — every document submitted to Companies House.

    Useful for tracing historical activity: incorporations, accounts, name changes,
    officer appointments, confirmation statements, etc.
    """
    out = await ch_client.get_company_filing_history(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.filings.FilingHistoryItem](
        items=[types.filings.FilingHistoryItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@filings_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_filing_history_item(
    company_number: CompanyNumberParam,
    filing_history_id: FilingHistoryIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.FilingHistoryItem | None:
    """Retrieve full detail for a single filing history transaction."""
    result = await ch_client.get_filing_history_item(company_number, filing_history_id)
    if result is None:
        return None
    return types.filings.FilingHistoryItem.from_api_t(result)


@filings_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_insolvency(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.CompanyInsolvency | None:
    """Retrieve insolvency cases recorded against a company.

    Returns ``None`` for most companies; populated for companies that have been or
    are subject to liquidation, administration, or similar proceedings.
    """
    result = await ch_client.get_company_insolvency(company_number)
    if result is None:
        return None
    return types.filings.CompanyInsolvency.from_api_t(result)


@filings_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_exemptions(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.filings.CompanyExemptions | None:
    """Retrieve any exemptions granted to a company (e.g. from certain PSC filing requirements)."""
    result = await ch_client.get_company_exemptions(company_number)
    if result is None:
        return None
    return types.filings.CompanyExemptions.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return filings_mcp
