"""Companies House company-level lookup tools."""

import logging
from typing import Annotated

import ch_api
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

from . import deps, types

logger = logging.getLogger(__name__)

CompanyNumberParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "The 8-character UK company number assigned by Companies House."
            " May include alpha prefixes (e.g. 'SC', 'NI', 'OC')."
            " Obtain this by calling search_companies first."
            " Example: '09370755'."
        ),
        min_length=1,
        max_length=10,
        pattern=r"^[A-Za-z0-9]{1,10}$",
    ),
]

companies_mcp = fastmcp.FastMCP("companies", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@companies_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_profile(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyProfile | None:
    """Retrieve the full Companies House profile for a UK company.

    Use this when you have a company number and need the company's registered name,
    status, incorporation date, accounting reference dates, SIC codes, and core
    registered details. If you do not have a company number, call search_companies
    first. Returns ``None`` if no company exists for the given number.
    """
    result = await ch_client.get_company_profile(company_number)
    if result is None:
        return None
    return types.company.CompanyProfile.from_api_t(result)


@companies_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def registered_office_address(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.RegisteredOfficeAddress | None:
    """Retrieve the current registered office address for a UK company.

    Use this when the user specifically asks for the address on record — the full
    profile (``get_company_profile``) already contains this as a sub-field, so prefer
    that when a broader picture is needed.
    """
    result = await ch_client.registered_office_address(company_number)
    if result is None:
        return None
    return types.company.RegisteredOfficeAddress.from_api_t(result)


@companies_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_registers(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyRegister | None:
    """Retrieve metadata about a company's statutory registers (directors, secretaries, PSC, etc.).

    Indicates whether each register is held at Companies House or on the company's
    single alternative inspection location.
    """
    result = await ch_client.get_company_registers(company_number)
    if result is None:
        return None
    return types.company.CompanyRegister.from_api_t(result)


@companies_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_uk_establishments(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyUKEstablishments | None:
    """Retrieve UK establishments (branches) registered under an overseas company.

    Only applicable to overseas companies that have registered a UK establishment;
    returns ``None`` for most domestic UK companies.
    """
    result = await ch_client.get_company_uk_establishments(company_number)
    if result is None:
        return None
    return types.company.CompanyUKEstablishments.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return companies_mcp
