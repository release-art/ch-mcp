"""Companies House search tools."""

import logging
from typing import Annotated

import ch_api
import ch_api.types.pagination.types as _ch_pagination
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

from . import auth, deps, types

logger = logging.getLogger(__name__)

search_mcp = fastmcp.FastMCP("search", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

_QueryParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Free-text query string passed to the Companies House search API."
            " Supports partial matches. Examples: 'Tesco', 'John Smith'."
        ),
        min_length=2,
    ),
]


@search_mcp.tool(
    annotations=_TOOL_ANNOTATIONS,
    tags={auth.tags.CH_API_RO},
)
async def search_companies(
    query: _QueryParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.CompanySearchItem]:
    """Search the UK Companies House register for companies by name or partial name match.

    Use this tool when the user mentions a company by name and you need to find its
    company number. The company number from the results is required by all
    get_company_* tools. Returns matching companies with their company number, name,
    status, and registered office. Does not return full company details — call
    get_company_profile with a specific company number for comprehensive information.
    """
    out = await ch_client.search_companies(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.CompanySearchItem](
        items=[types.search.CompanySearchItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def search_officers(
    query: _QueryParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.OfficerSearchItem]:
    """Search the UK Companies House register for company officers by name.

    Use this tool when the user asks about a specific director, secretary, or other
    company officer, or when you need to look up an officer ID. The officer ID from
    the results is required to call get_officer_appointments. Returns matching
    officers with their identifier, name, and a sample appointment.
    """
    out = await ch_client.search_officers(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.OfficerSearchItem](
        items=[types.search.OfficerSearchItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def search_disqualified_officers(
    query: _QueryParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.DisqualifiedOfficerSearchItem]:
    """Search for officers who have been disqualified from acting as a UK company director.

    Use this tool to check whether a person appears on the public register of
    disqualified directors. Follow up with get_natural_officer_disqualification or
    get_corporate_officer_disqualification for full disqualification details.
    """
    out = await ch_client.search_disqualified_officers(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.DisqualifiedOfficerSearchItem](
        items=[types.search.DisqualifiedOfficerSearchItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def alphabetical_companies_search(
    query: _QueryParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.AlphabeticalCompany]:
    """Alphabetical company search — finds companies whose names appear near ``query`` alphabetically.

    Useful for browsing the register in alphabetical order from a given starting
    point. For ranked relevance search prefer ``search_companies``.
    """
    out = await ch_client.alphabetical_companies_search(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.AlphabeticalCompany](
        items=[types.search.AlphabeticalCompany.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def search_dissolved_companies(
    query: _QueryParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.DissolvedCompany]:
    """Search the register of dissolved UK companies by name.

    Use this to investigate companies that no longer exist on the live register.
    """
    out = await ch_client.search_dissolved_companies(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.DissolvedCompany](
        items=[types.search.DissolvedCompany.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def advanced_company_search(
    company_name_includes: Annotated[
        str | None,
        pydantic.Field(default=None, description="Words the name must include."),
    ] = None,
    company_name_excludes: Annotated[
        str | None,
        pydantic.Field(default=None, description="Words the name must NOT include."),
    ] = None,
    company_status: Annotated[
        list[str] | None,
        pydantic.Field(default=None, description="Filter by company status (e.g. 'active', 'dissolved')."),
    ] = None,
    company_type: Annotated[
        list[str] | None,
        pydantic.Field(default=None, description="Filter by company type (e.g. 'ltd', 'plc')."),
    ] = None,
    location: Annotated[str | None, pydantic.Field(default=None, description="Registered office locality.")] = None,
    sic_codes: Annotated[
        list[str] | None,
        pydantic.Field(default=None, description="Filter by SIC codes (industry classification)."),
    ] = None,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.AdvancedCompany]:
    """Advanced company search with structured filters (name tokens, status, type, SIC codes, location).

    Prefer this over ``search_companies`` when the user asks for companies matching
    multiple criteria (e.g. "active plcs in Manchester with SIC 62020").
    """
    out = await ch_client.advanced_company_search(
        company_name_includes=company_name_includes,
        company_name_excludes=company_name_excludes,
        company_status=company_status,
        company_type=company_type,
        location=location,
        sic_codes=sic_codes,
        next_page=next_page_token,
    )
    return types.pagination.MultipageList[types.search.AdvancedCompany](
        items=[types.search.AdvancedCompany.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


def get_server() -> fastmcp.FastMCP:
    return search_mcp
