"""FCA-regulated firm lookup tools"""

import logging
from typing import Annotated

import fastmcp
import fca_api
import pydantic
from mcp.types import ToolAnnotations

from . import deps, types

logger = logging.getLogger(__name__)

FrnParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "The Firm Reference Number (FRN), a unique numeric identifier assigned by the FCA"
            " to each regulated firm. Obtain this by calling search_frn first. Example: '122702'."
        ),
    ),
]

firms_mcp = fastmcp.FastMCP("search-firms", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm(frn: FrnParam, fca_client: fca_api.async_api.Client = deps.FcaApiDep) -> types.firm.FirmDetails:
    """Retrieve detailed regulatory information about a specific FCA-regulated firm.

    Use this tool when you have a Firm Reference Number (FRN) and need the firm's full
    profile, including its registered name, current status, and core regulatory details.
    If you do not have an FRN, call search_frn first with the firm name. Returns core
    firm details only — use the other get_firm_* tools for specific aspects like
    permissions, individuals, addresses, or disciplinary history.
    """
    result = await fca_client.get_firm(frn)
    return types.firm.FirmDetails.from_api_t(result)


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_names(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmNameAlias]:
    """Retrieve all registered names and trading name aliases for a specific FCA-regulated firm.

    Use this tool to find alternative, former, or trading names a firm has used. Useful
    for verifying whether two different names refer to the same regulated entity. If you
    do not have an FRN, call search_frn first with the firm name.
    """
    out = await fca_client.get_firm_names(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmNameAlias](
        items=[types.firm.FirmNameAlias.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_addresses(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmAddress]:
    """Retrieve all registered addresses for a specific FCA-regulated firm, including current and historical addresses.

    Use this tool when you need a firm's physical location, correspondence address, or
    want to trace address changes over time. If you do not have an FRN, call search_frn
    first with the firm name.
    """
    out = await fca_client.get_firm_addresses(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmAddress](
        items=[types.firm.FirmAddress.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_controlled_functions(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmControlledFunction]:
    """Retrieve the controlled functions held at a specific FCA-regulated firm.

    Controlled functions are senior management or customer-facing roles that require FCA
    approval (e.g., CF1 Director, CF10 Compliance Oversight, CF30 Customer Function). Use
    this tool to see which regulated roles exist at a firm. If you do not have an FRN,
    call search_frn first. To find which specific individuals hold these roles, use
    get_firm_individuals instead.
    """
    out = await fca_client.get_firm_controlled_functions(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmControlledFunction](
        items=[types.firm.FirmControlledFunction.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_individuals(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmIndividual]:
    """Retrieve all FCA-registered individuals associated with a specific firm.

    Returns individuals and the controlled functions (regulated roles) they hold at the
    firm, such as directors, compliance officers, and approved persons. Use this tool to
    find out who holds regulated roles at a firm. If you do not have an FRN, call
    search_frn first. For detailed information about a specific individual, use their IRN
    with get_individual.
    """
    out = await fca_client.get_firm_individuals(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmIndividual](
        items=[types.firm.FirmIndividual.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_permissions(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmPermission]:
    """Retrieve the regulatory permissions granted to a specific FCA-regulated firm.

    Permissions define what regulated activities a firm is authorized to carry out, such
    as accepting deposits, arranging deals in investments, or insurance mediation. Use
    this tool to verify what a firm is authorized to do under FCA regulation. If you do
    not have an FRN, call search_frn first with the firm name.
    """
    out = await fca_client.get_firm_permissions(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmPermission](
        items=[types.firm.FirmPermission.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_requirements(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmRequirement]:
    """Retrieve regulatory requirements imposed on a specific FCA-regulated firm.

    Requirements are conditions or restrictions placed on a firm's authorization by the
    FCA, such as capital requirements or reporting obligations. Use this tool to check
    constraints on a firm's operations. If you do not have an FRN, call search_frn first.
    To see which investment types a specific requirement applies to, use
    get_firm_requirement_investment_types with the requirement reference from these results.
    """
    out = await fca_client.get_firm_requirements(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmRequirement](
        items=[types.firm.FirmRequirement.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_requirement_investment_types(
    frn: FrnParam,
    req_ref: Annotated[
        str,
        pydantic.Field(
            description="The requirement reference identifier, obtained from get_firm_requirements results.",
        ),
    ],
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmRequirementInvestmentType]:
    """Retrieve the investment types associated with a specific regulatory requirement for an FCA-regulated firm.

    Use this tool after calling get_firm_requirements to drill into which investment types
    a particular requirement applies to. Requires both a Firm Reference Number (FRN) and
    a requirement reference (req_ref) obtained from get_firm_requirements results.
    """
    out = await fca_client.get_firm_requirement_investment_types(frn, req_ref, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmRequirementInvestmentType](
        items=[types.firm.FirmRequirementInvestmentType.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_regulators(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmRegulator]:
    """Retrieve the regulators responsible for overseeing a specific firm.

    Most FCA-regulated firms are overseen by the FCA alone, but some (e.g., banks,
    insurers) are dual-regulated by both the FCA and the PRA (Prudential Regulation
    Authority). Use this tool to determine which regulatory bodies have jurisdiction
    over a firm. If you do not have an FRN, call search_frn first.
    """
    out = await fca_client.get_firm_regulators(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmRegulator](
        items=[types.firm.FirmRegulator.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_passports(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmPassport]:
    """Retrieve the regulatory passports held by a specific FCA-regulated firm.

    Passports (under pre-Brexit EEA arrangements) allow a firm authorized in one
    jurisdiction to operate in other countries without separate authorization. Use this
    tool to find which countries a firm has passported into. If you do not have an FRN,
    call search_frn first. To see specific permissions in a passported country, use
    get_firm_passport_permissions with the country from these results.
    """
    out = await fca_client.get_firm_passports(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmPassport](
        items=[types.firm.FirmPassport.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_passport_permissions(
    frn: FrnParam,
    country: Annotated[
        str,
        pydantic.Field(
            description=(
                "The country name for which to retrieve passport permissions, obtained from get_firm_passports results."
            ),
        ),
    ],
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmPassportPermission]:
    """Retrieve the specific permissions a firm holds under its regulatory passport in a given country.

    Use this tool after calling get_firm_passports to drill into what a firm is authorized
    to do in a specific passported jurisdiction. Requires both a Firm Reference Number
    (FRN) and a country name obtained from get_firm_passports results.
    """
    out = await fca_client.get_firm_passport_permissions(frn, country, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmPassportPermission](
        items=[types.firm.FirmPassportPermission.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_waivers(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmWaiver]:
    """Retrieve any regulatory waivers granted to a specific FCA-regulated firm.

    Waivers are formal modifications to regulatory rules that the FCA has granted to a
    firm, allowing it to deviate from standard requirements under specific conditions.
    Use this tool to check if a firm has been granted any special regulatory concessions.
    If you do not have an FRN, call search_frn first.
    """
    out = await fca_client.get_firm_waivers(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmWaiver](
        items=[types.firm.FirmWaiver.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_exclusions(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmExclusion]:
    """Retrieve any exclusions that apply to a specific FCA-regulated firm.

    Exclusions define specific regulated activities or products that a firm is explicitly
    not authorized to carry out, narrowing the scope of its permissions. Use this tool to
    understand limitations on a firm's authorization. If you do not have an FRN, call
    search_frn first.
    """
    out = await fca_client.get_firm_exclusions(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmExclusion](
        items=[types.firm.FirmExclusion.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_disciplinary_history(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmDisciplinaryRecord]:
    """Retrieve the disciplinary history of a specific FCA-regulated firm.

    Returns records of enforcement actions, fines, public censures, or other disciplinary
    measures taken against the firm by the FCA. Use this tool when assessing a firm's
    compliance track record or checking for past regulatory sanctions. If you do not have
    an FRN, call search_frn first.
    """
    out = await fca_client.get_firm_disciplinary_history(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmDisciplinaryRecord](
        items=[types.firm.FirmDisciplinaryRecord.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@firms_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_firm_appointed_representatives(
    frn: FrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.firm.FirmAppointedRepresentative]:
    """Retrieve the appointed representatives (ARs) of a specific FCA-regulated firm.

    Appointed representatives are firms or individuals authorized to carry out regulated
    activities under the responsibility of a principal firm, rather than being directly
    authorized by the FCA themselves. Use this tool to find which entities operate under
    a firm's regulatory umbrella. If you do not have an FRN, call search_frn first.
    """
    out = await fca_client.get_firm_appointed_representatives(frn, next_page=next_page_token)
    return types.pagination.MultipageList[types.firm.FirmAppointedRepresentative](
        items=[types.firm.FirmAppointedRepresentative.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


def get_server() -> fastmcp.FastMCP:
    return firms_mcp
