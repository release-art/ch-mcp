"""Companies House officer lookup tools."""

import logging
from typing import Annotated, Literal

import ch_api
import ch_api.types.pagination.types as _ch_pagination
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

from . import auth, deps, types
from .companies import CompanyNumberParam

logger = logging.getLogger(__name__)

OfficerIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Opaque Companies House officer identifier (a URL-safe base64 string)."
            " Copy from the ``refs.officer_id`` field of a ``search_officers`` hit,"
            " a ``get_officer_list`` item, or a ``search_disqualified_officers`` hit."
        ),
        min_length=1,
    ),
]

DisqualificationKindParam = Annotated[
    Literal["natural-disqualification", "corporate-disqualification"],
    pydantic.Field(
        description=(
            "Whether the disqualified officer is a natural person (human) or a"
            " corporate body. ``search_disqualified_officers`` items distinguish"
            " these via their ``date_of_birth`` field (present only for naturals)"
            " — use ``natural-disqualification`` for humans and"
            " ``corporate-disqualification`` for companies acting as directors."
        ),
    ),
]

officers_mcp = fastmcp.FastMCP("officers", on_duplicate="error")

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


@officers_mcp.tool(**_TOOL_KW)
async def get_officer_list(
    company_number: CompanyNumberParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.officer.OfficerSummary]:
    """List the officers currently or formerly appointed at a specific company.

    Covers directors, secretaries, and LLP members. Each entry carries an
    ``appointment_id`` (scoped to this company) and an ``officer_id`` (the person's
    global identifier) that can be passed to ``get_officer_appointments`` to see
    every company the same person serves.
    """
    out = await ch_client.get_officer_list(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.officer.OfficerSummary](
        items=[types.officer.OfficerSummary.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@officers_mcp.tool(**_TOOL_KW)
async def get_officer_appointments(
    officer_id: OfficerIdParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.officer.OfficerAppointmentSummary]:
    """List every company appointment (current and past) held by a given officer.

    Use this after ``search_officers`` or ``get_officer_list`` to see the full
    directorship history of a person across the entire UK register. Each entry
    includes the company number, the role, and appointment/resignation dates.
    """
    out = await ch_client.get_officer_appointments(officer_id, next_page=next_page_token)
    return types.pagination.MultipageList[types.officer.OfficerAppointmentSummary](
        items=[types.officer.OfficerAppointmentSummary.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@officers_mcp.tool(**_TOOL_KW)
async def get_officer_disqualification(
    officer_id: OfficerIdParam,
    kind: DisqualificationKindParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.OfficerDisqualificationRecord | None:
    """Fetch the full disqualification order for an officer.

    One tool covers both disqualification variants:

    - ``natural-disqualification`` for human directors — returns reasons,
      date ranges, nationality, any permission-to-act grants, and prior
      variations.
    - ``corporate-disqualification`` for companies acting as directors —
      returns reasons, date ranges, and the corporate entity's identifiers.

    Use after ``search_disqualified_officers``: pick the ``kind`` from the
    nature of the hit (humans have a date_of_birth field; corporates do not).
    The response is a discriminated union keyed on its own ``kind`` field so
    MCP clients can statically narrow to the right variant.
    """
    if kind == "natural-disqualification":
        result = await ch_client.get_natural_officer_disqualification(officer_id)
        return types.officer.NaturalDisqualification.from_api_t(result) if result is not None else None
    result = await ch_client.get_corporate_officer_disqualification(officer_id)
    return types.officer.CorporateDisqualification.from_api_t(result) if result is not None else None


def get_server() -> fastmcp.FastMCP:
    return officers_mcp
