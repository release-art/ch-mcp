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

_TOOL_KW = {
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    "tags": {auth.tags.CH_API_RO},
}

_QueryParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Free-text search query. Matched against company or officer names by the"
            " Companies House search engine (case-insensitive, fuzzy). Examples:"
            " 'Tesco', 'Revolut', 'John Smith'."
        ),
        min_length=2,
    ),
]

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


@search_mcp.tool(**_TOOL_KW)
async def search_companies(
    query: _QueryParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.CompanySearchItem]:
    """Find UK companies by name using the Companies House search engine.

    Returns matches with company number, name, current status, incorporation date,
    and registered office. Call this first when the user mentions a company by name —
    the returned company_number is the key required by every ``get_company_*`` tool.
    For richer filtering (status/type/SIC/location) use ``advanced_company_search``;
    for dissolved-only results use ``search_dissolved_companies``.
    """
    out = await ch_client.search_companies(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.CompanySearchItem](
        items=[types.search.CompanySearchItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(**_TOOL_KW)
async def search_officers(
    query: _QueryParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.OfficerSearchItem]:
    """Find company officers (directors, secretaries, LLP members) by name.

    Returns matches with an opaque officer_id, the officer's name, and a sample
    appointment. Call this when the user asks about an individual by name; the
    returned officer_id feeds ``get_officer_appointments`` to list every company
    they are or were on the board of.
    """
    out = await ch_client.search_officers(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.OfficerSearchItem](
        items=[types.search.OfficerSearchItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(**_TOOL_KW)
async def search_disqualified_officers(
    query: _QueryParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.DisqualifiedOfficerSearchItem]:
    """Find officers on the public register of disqualified UK company directors.

    Use this to check whether a named person has been banned from acting as a
    director. The returned officer_id can be passed to
    ``get_natural_officer_disqualification`` (for humans) or
    ``get_corporate_officer_disqualification`` (for companies acting as directors)
    to retrieve the full disqualification order.
    """
    out = await ch_client.search_disqualified_officers(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.DisqualifiedOfficerSearchItem](
        items=[types.search.DisqualifiedOfficerSearchItem.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(**_TOOL_KW)
async def alphabetical_companies_search(
    query: _QueryParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.AlphabeticalCompany]:
    """Browse UK companies alphabetically starting from a given name prefix.

    Results are ordered by company name, not by relevance. Prefer
    ``search_companies`` for fuzzy/ranked matching; use this only when the user
    explicitly wants alphabetical ordering (e.g. "list companies starting with
    'Acme'").
    """
    out = await ch_client.alphabetical_companies_search(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.AlphabeticalCompany](
        items=[types.search.AlphabeticalCompany.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(**_TOOL_KW)
async def search_dissolved_companies(
    query: _QueryParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.DissolvedCompany]:
    """Find companies that have been dissolved (no longer on the live register) by name.

    Returns matches with company number, previous names, and dates of incorporation
    and dissolution. Use this when the user is researching a company that may have
    been struck off or liquidated. For currently-active companies use
    ``search_companies`` instead.
    """
    out = await ch_client.search_dissolved_companies(query, next_page=next_page_token)
    return types.pagination.MultipageList[types.search.DissolvedCompany](
        items=[types.search.DissolvedCompany.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@search_mcp.tool(**_TOOL_KW)
async def advanced_company_search(
    company_name_includes: Annotated[
        str | None,
        pydantic.Field(
            default=None,
            description="Substring that must appear in the company name.",
        ),
    ] = None,
    company_name_excludes: Annotated[
        str | None,
        pydantic.Field(
            default=None,
            description="Substring that must NOT appear in the company name.",
        ),
    ] = None,
    company_status: Annotated[
        list[str] | None,
        pydantic.Field(
            default=None,
            description=(
                "Filter by registration status. Valid values include: 'active',"
                " 'dissolved', 'liquidation', 'receivership', 'administration',"
                " 'voluntary-arrangement', 'converted-closed', 'insolvency-proceedings',"
                " 'registered', 'removed', 'open', 'closed'."
            ),
        ),
    ] = None,
    company_type: Annotated[
        list[str] | None,
        pydantic.Field(
            default=None,
            description=(
                "Filter by company type. Common values: 'ltd' (private limited),"
                " 'plc' (public limited), 'llp' (limited liability partnership),"
                " 'charitable-incorporated-organisation', 'community-interest-company',"
                " 'limited-partnership', 'private-unlimited', 'registered-society-non-jurisdictional'."
            ),
        ),
    ] = None,
    location: Annotated[
        str | None,
        pydantic.Field(
            default=None,
            description=(
                "Filter by registered office locality. Free-text match against the"
                " registered office locality field (typically a town or city)."
            ),
        ),
    ] = None,
    sic_codes: Annotated[
        list[str] | None,
        pydantic.Field(
            default=None,
            description=(
                "Filter by UK SIC 2007 industry classification codes. Pass a list of"
                " 5-digit codes as strings (e.g. ['62020', '62090'] for IT consulting)."
            ),
        ),
    ] = None,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.search.AdvancedCompany]:
    """Search UK companies with structured filters (name tokens, status, type, SIC, location).

    Prefer this over ``search_companies`` when the user wants to narrow by multiple
    criteria (e.g. "active PLCs in Manchester with SIC 62020"). All filters are
    optional; at least one filter should be provided to keep the result set small.
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
