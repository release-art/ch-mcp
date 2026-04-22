"""Companies House officer lookup tools."""

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

OfficerIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Opaque Companies House officer identifier (a URL-safe base64 string)."
            " Obtain from the ``officer_id`` field of ``search_officers`` results or"
            " from the officer list of a specific company."
        ),
        min_length=1,
    ),
]

AppointmentIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Opaque appointment identifier scoped to a single company. Obtain from"
            " the ``appointment_id`` field of ``get_officer_list`` items."
        ),
        min_length=1,
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
async def get_officer_appointment(
    company_number: CompanyNumberParam,
    appointment_id: AppointmentIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.OfficerSummary | None:
    """Fetch a single officer appointment at a specific company.

    ``appointment_id`` is the per-company appointment key returned by
    ``get_officer_list``. Use this to refresh a single appointment when you
    already have its id; otherwise start from ``get_officer_list``.
    """
    result = await ch_client.get_officer_appointment(company_number, appointment_id)
    if result is None:
        return None
    return types.officer.OfficerSummary.from_api_t(result)


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
async def get_natural_officer_disqualification(
    officer_id: OfficerIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.NaturalDisqualification | None:
    """Fetch the full disqualification order for a natural-person (human) officer.

    Returns reasons, date ranges, any permission-to-act grants, and prior
    variations. Use after ``search_disqualified_officers`` with an officer_id
    for a human director. Returns ``None`` if the officer is corporate or not
    disqualified — in the corporate case call
    ``get_corporate_officer_disqualification`` instead.
    """
    result = await ch_client.get_natural_officer_disqualification(officer_id)
    if result is None:
        return None
    return types.officer.NaturalDisqualification.from_api_t(result)


@officers_mcp.tool(**_TOOL_KW)
async def get_corporate_officer_disqualification(
    officer_id: OfficerIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.CorporateDisqualification | None:
    """Fetch the full disqualification order for a corporate officer (a company acting as director).

    Returns reasons, date ranges, and the corporate entity's identifying details.
    Use after ``search_disqualified_officers`` when the hit represents a company
    rather than an individual. For natural-person disqualifications call
    ``get_natural_officer_disqualification`` instead.
    """
    result = await ch_client.get_corporate_officer_disqualification(officer_id)
    if result is None:
        return None
    return types.officer.CorporateDisqualification.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return officers_mcp
