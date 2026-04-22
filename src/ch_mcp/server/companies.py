"""Companies House company-level lookup tools."""

import logging
from typing import Annotated

import ch_api
import fastmcp
import pydantic
from mcp.types import ToolAnnotations

from . import auth, deps, types

logger = logging.getLogger(__name__)

CompanyNumberParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "UK company number assigned by Companies House. 1-10 alphanumeric"
            " characters, typically 8 digits, possibly with an alpha prefix"
            " (e.g. 'SC' for Scotland, 'NI' for Northern Ireland, 'OC' for an LLP)."
            " Obtain via ``search_companies`` if you do not already have it."
            " Examples: '09370755', 'SC123456', 'OC301550'."
        ),
        min_length=1,
        max_length=10,
        pattern=r"^[A-Za-z0-9]{1,10}$",
    ),
]

companies_mcp = fastmcp.FastMCP("companies", on_duplicate="error")

_TOOL_KW = {
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    "tags": {auth.tags.CH_API_RO},
}


@companies_mcp.tool(**_TOOL_KW)
async def get_company_profile(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyProfile | None:
    """Fetch the full Companies House profile for a UK company.

    Returns registered name, status, company type, incorporation/dissolution dates,
    registered office, accounting reference dates, SIC codes, and previous names.
    This is usually the first call after you have a company_number — it gives the
    broadest single view of the company. Returns ``None`` if the number does not
    resolve to a known company.
    """
    result = await ch_client.get_company_profile(company_number)
    if result is None:
        return None
    return types.company.CompanyProfile.from_api_t(result)


@companies_mcp.tool(**_TOOL_KW)
async def get_company_registers(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyRegister | None:
    """Report where a company holds each of its statutory registers.

    Indicates, per register type (directors, secretaries, members, PSCs, LLP
    members, usual residential addresses), whether the register is kept at
    Companies House or at the company's Single Alternative Inspection Location
    (SAIL). Use this when investigating where to formally inspect a register;
    most users will not need this.
    """
    result = await ch_client.get_company_registers(company_number)
    if result is None:
        return None
    return types.company.CompanyRegister.from_api_t(result)


@companies_mcp.tool(**_TOOL_KW)
async def get_company_uk_establishments(
    company_number: CompanyNumberParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.company.CompanyUKEstablishments | None:
    """List UK establishments (branches) of an overseas-incorporated company.

    Only applies to overseas companies (``company_type`` = ``oversea-company``)
    that have registered one or more establishments in the UK. Returns ``None``
    for purely UK-incorporated companies.
    """
    result = await ch_client.get_company_uk_establishments(company_number)
    if result is None:
        return None
    return types.company.CompanyUKEstablishments.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return companies_mcp
