"""Persons with Significant Control (PSC) tools."""

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

PscIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Companies House PSC identifier, as returned in the ``links`` of items from"
            " ``get_company_psc_list`` (URL-safe base64-encoded substring)."
        ),
        min_length=1,
    ),
]

psc_mcp = fastmcp.FastMCP("psc", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_psc_list(
    company_number: CompanyNumberParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.psc.ListSummary]:
    """List all persons with significant control (PSCs) declared for a UK company.

    PSCs are people or entities that ultimately own or control a company. Each entry
    indicates the kind of control and carries an identifier for drilling into the
    concrete PSC type (``get_company_individual_psc``,
    ``get_company_corporate_psc``, etc.).
    """
    out = await ch_client.get_company_psc_list(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.psc.ListSummary](
        items=[types.psc.ListSummary.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_psc_statements(
    company_number: CompanyNumberParam,
    next_page_token: _ch_pagination.NextPageToken | None = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.psc.Statement]:
    """Retrieve PSC statements recorded against a company.

    Statements are formal declarations about PSC status (e.g. "no PSC", "investigation
    ongoing"). Complements ``get_company_psc_list``.
    """
    out = await ch_client.get_company_psc_statements(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.psc.Statement](
        items=[types.psc.Statement.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_individual_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.Individual | None:
    """Retrieve the full record of an individual (natural person) PSC at a company."""
    result = await ch_client.get_company_individual_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.Individual.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_individual_psc_beneficial_owner(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.IndividualBeneficialOwner | None:
    """Retrieve the full record of an individual registrable beneficial owner."""
    result = await ch_client.get_company_individual_psc_beneficial_owner(company_number, psc_id)
    if result is None:
        return None
    return types.psc.IndividualBeneficialOwner.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_corporate_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.CorporateEntity | None:
    """Retrieve the full record of a corporate-entity PSC (a company exercising control over another)."""
    result = await ch_client.get_company_corporate_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.CorporateEntity.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_corporate_psc_beneficial_owner(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.CorporateEntityBeneficialOwner | None:
    """Retrieve the full record of a corporate registrable beneficial owner."""
    result = await ch_client.get_company_corporate_psc_beneficial_owner(company_number, psc_id)
    if result is None:
        return None
    return types.psc.CorporateEntityBeneficialOwner.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_legal_person_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.LegalPerson | None:
    """Retrieve the full record of a legal-person PSC (a non-company legal entity)."""
    result = await ch_client.get_company_legal_person_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.LegalPerson.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_legal_person_psc_beneficial_owner(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.LegalPersonBeneficialOwner | None:
    """Retrieve the full record of a legal-person registrable beneficial owner."""
    result = await ch_client.get_company_legal_person_psc_beneficial_owner(company_number, psc_id)
    if result is None:
        return None
    return types.psc.LegalPersonBeneficialOwner.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_super_secure_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.SuperSecure | None:
    """Retrieve the record of a super-secure PSC (personal details protected for safety)."""
    result = await ch_client.get_company_super_secure_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.SuperSecure.from_api_t(result)


@psc_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_company_super_secure_beneficial_owner_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.SuperSecureBeneficialOwner | None:
    """Retrieve the record of a super-secure registrable beneficial owner."""
    result = await ch_client.get_company_super_secure_beneficial_owner_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.SuperSecureBeneficialOwner.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return psc_mcp
