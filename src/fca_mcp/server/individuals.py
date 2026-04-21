import logging
from typing import Annotated

import fastmcp
import fca_api
import pydantic
from mcp.types import ToolAnnotations

from . import deps, types

logger = logging.getLogger(__name__)

IrnParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "The Individual Reference Number (IRN), a unique identifier assigned by the FCA"
            " to each registered individual. Obtain this by calling search_irn first."
        ),
    ),
]

individuals_mcp = fastmcp.FastMCP("search-individuals", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@individuals_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_individual(
    irn: IrnParam, fca_client: fca_api.async_api.Client = deps.FcaApiDep
) -> types.individual.Individual:
    """Retrieve detailed information about a specific FCA-registered individual.

    Use this tool when you have an Individual Reference Number (IRN) and need the person's
    full profile, including their name, status, and associated firms. If you do not have an
    IRN, call search_irn first with the person's name. Returns core individual details
    only — use get_individual_controlled_functions for their regulated roles and
    get_individual_disciplinary_history for any enforcement actions.
    """
    out = await fca_client.get_individual(irn)
    return types.individual.Individual.from_api_t(out)


@individuals_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_individual_controlled_functions(
    irn: IrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.individual.IndividualControlledFunction]:
    """Retrieve the controlled functions held by a specific FCA-registered individual across all associated firms.

    Controlled functions are FCA-approved roles such as Director (CF1), Compliance Oversight
    (CF10), or Customer Function (CF30). Use this tool to check what regulated roles a person
    holds or has held, and at which firms. If you do not have an IRN, call search_irn first
    with the person's name.
    """
    out = await fca_client.get_individual_controlled_functions(irn, next_page=next_page_token)
    return types.pagination.MultipageList[types.individual.IndividualControlledFunction](
        items=[types.individual.IndividualControlledFunction.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@individuals_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_individual_disciplinary_history(
    irn: IrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.individual.IndividualDisciplinaryRecord]:
    """Retrieve the disciplinary history of a specific FCA-registered individual.

    Returns records of enforcement actions, prohibitions, fines, or other regulatory
    sanctions taken against the individual by the FCA. Use this tool when assessing a
    person's regulatory compliance track record or checking for past sanctions. If you
    do not have an IRN, call search_irn first with the person's name.
    """
    out = await fca_client.get_individual_disciplinary_history(irn, next_page=next_page_token)
    return types.pagination.MultipageList[types.individual.IndividualDisciplinaryRecord](
        items=[types.individual.IndividualDisciplinaryRecord.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


def get_server() -> fastmcp.FastMCP:
    return individuals_mcp
