import logging
from typing import Annotated

import fastmcp
import fca_api
import pydantic
from mcp.types import ToolAnnotations

from . import auth, deps, types

logger = logging.getLogger(__name__)


search_mcp = fastmcp.FastMCP("search-firms", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@search_mcp.tool(
    annotations=_TOOL_ANNOTATIONS,
    tags={
        auth.tags.FCA_API_RO,
    },
)
async def search_frn(
    firm_name: Annotated[
        str,
        pydantic.Field(
            description=(
                "The firm name or partial name to search for."
                " Supports partial matches."
                " Examples: 'Barclays', 'HSBC', 'Goldman Sachs'."
            ),
            min_length=3,
        ),
    ],
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.search.FirmSearchResult]:
    """Search the UK FCA Financial Services Register for regulated firms by name or partial name match.

    Use this tool when the user asks about a financial firm, wants to verify if a company is
    FCA-regulated, or when you need to look up a Firm Reference Number (FRN). The FRN from
    the results is required by all get_firm_* tools. Returns matching firms with their FRN,
    name, and status. Does not return detailed firm information — call get_firm with a
    specific FRN for full details.
    """
    out = await fca_client.search_frn(firm_name, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.FirmSearchResult](
        items=[types.search.FirmSearchResult.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def search_irn(
    individual_name: Annotated[
        str,
        pydantic.Field(
            description="The individual's name or partial name to search for. Examples: 'John Smith', 'Smith'.",
            min_length=2,
        ),
    ],
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.search.IndividualSearchResult]:
    """Search the UK FCA Financial Services Register for registered individuals by name.

    Use this tool when the user asks about a specific person in financial services, wants to
    check if someone is FCA-registered, or when you need to look up an Individual Reference
    Number (IRN). The IRN from the results is required by all get_individual_* tools. Returns
    matching individuals with their IRN and name. Does not return role or disciplinary
    details — call get_individual with a specific IRN for full details.
    """
    out = await fca_client.search_irn(individual_name, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.IndividualSearchResult](
        items=[types.search.IndividualSearchResult.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def search_prn(
    fund_name: Annotated[
        str,
        pydantic.Field(
            description="The fund name or partial name to search for. Examples: 'Vanguard', 'iShares', 'BlackRock'.",
            min_length=2,
        ),
    ],
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.search.FundSearchResult]:
    """Search the UK FCA Financial Services Register for investment funds by name or partial name match.

    Use this tool when the user asks about a specific investment fund, wants to verify if a
    fund is FCA-registered, or when you need to look up a Product Reference Number (PRN). The
    PRN from the results is required by all get_fund_* tools. Returns matching funds with
    their PRN and name. Does not return full fund details — call get_fund with a specific PRN
    for comprehensive information.
    """
    out = await fca_client.search_prn(fund_name, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.FundSearchResult](
        items=[types.search.FundSearchResult.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


def get_server() -> fastmcp.FastMCP:
    return search_mcp
