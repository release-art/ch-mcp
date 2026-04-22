"""Companies House officer lookup tools."""

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

OfficerIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Companies House officer identifier (the opaque ID shown in search_officers"
            " results and in officer_list entries)."
        ),
        min_length=1,
    ),
]

AppointmentIdParam = Annotated[
    str,
    pydantic.Field(
        description="Companies House appointment identifier for a specific officer appointment at a company.",
        min_length=1,
    ),
]

officers_mcp = fastmcp.FastMCP("officers", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@officers_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_officer_list(
    company_number: CompanyNumberParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.officer.OfficerSummary]:
    """List the officers (directors, secretaries, LLP members) appointed at a company.

    Use this to discover who runs a company. Each entry carries an officer identifier
    that can be passed to ``get_officer_appointments`` to see every company that
    person is on the board of.
    """
    out = await ch_client.get_officer_list(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.officer.OfficerSummary](
        items=[types.officer.OfficerSummary.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@officers_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_officer_appointment(
    company_number: CompanyNumberParam,
    appointment_id: AppointmentIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.OfficerSummary | None:
    """Retrieve a single officer appointment at a specific company by appointment ID."""
    result = await ch_client.get_officer_appointment(company_number, appointment_id)
    if result is None:
        return None
    return types.officer.OfficerSummary.from_api_t(result)


@officers_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_officer_appointments(
    officer_id: OfficerIdParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.officer.OfficerAppointmentSummary]:
    """List every company appointment held (current and past) by a given officer.

    Use this after ``search_officers`` or ``get_officer_list`` to see the full career
    of a director or secretary across the register.
    """
    out = await ch_client.get_officer_appointments(officer_id, next_page=next_page_token)
    return types.pagination.MultipageList[types.officer.OfficerAppointmentSummary](
        items=[types.officer.OfficerAppointmentSummary.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@officers_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_natural_officer_disqualification(
    officer_id: OfficerIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.NaturalDisqualification | None:
    """Retrieve the full disqualification record for a natural-person officer.

    Use after ``search_disqualified_officers`` with a natural (human) officer ID.
    """
    result = await ch_client.get_natural_officer_disqualification(officer_id)
    if result is None:
        return None
    return types.officer.NaturalDisqualification.from_api_t(result)


@officers_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_corporate_officer_disqualification(
    officer_id: OfficerIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.officer.CorporateDisqualification | None:
    """Retrieve the full disqualification record for a corporate officer (a company acting as a director).

    Use after ``search_disqualified_officers`` with a corporate officer ID.
    """
    result = await ch_client.get_corporate_officer_disqualification(officer_id)
    if result is None:
        return None
    return types.officer.CorporateDisqualification.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return officers_mcp
