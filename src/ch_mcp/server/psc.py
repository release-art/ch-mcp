"""Persons with Significant Control (PSC) tools.

Companies House records five kinds of PSC, each with a "beneficial owner" variant:

- **individual** — a natural person exercising control.
- **corporate-entity** — a registered company exercising control.
- **legal-person** — a non-company legal entity (e.g. a trust, foundation).
- **super-secure** — a person whose details are withheld for safety.

Call ``get_company_psc_list`` first to enumerate a company's PSCs; each entry's
``kind`` tells you which ``get_company_{kind}_psc`` tool to use for the full
record.
"""

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

PscIdParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "Opaque PSC notification identifier. Extract from the ``notification_id``"
            " field of ``get_company_psc_list`` items, or from the trailing path"
            " segment of the item's ``self`` link."
        ),
        min_length=1,
    ),
]

psc_mcp = fastmcp.FastMCP("psc", on_duplicate="error")

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


@psc_mcp.tool(**_TOOL_KW)
async def get_company_psc_list(
    company_number: CompanyNumberParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.psc.ListSummary]:
    """List the persons with significant control (PSCs) declared for a company.

    PSCs are the individuals or entities that ultimately own or control the
    company (typically >25% of shares, >25% of voting rights, or right to appoint
    directors). Each entry's ``kind`` field indicates which specific
    ``get_company_{kind}_psc`` tool to call for the full record.
    """
    out = await ch_client.get_company_psc_list(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.psc.ListSummary](
        items=[types.psc.ListSummary.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@psc_mcp.tool(**_TOOL_KW)
async def get_company_psc_statements(
    company_number: CompanyNumberParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.psc.Statement]:
    """List PSC statements recorded against a company.

    Statements are formal declarations about PSC status rather than concrete PSCs
    (e.g. "the company has no registrable person with significant control",
    "investigation ongoing"). Complements ``get_company_psc_list`` — a company may
    have statements but no listed PSCs, or vice versa.
    """
    out = await ch_client.get_company_psc_statements(company_number, next_page=next_page_token)
    return types.pagination.MultipageList[types.psc.Statement](
        items=[types.psc.Statement.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@psc_mcp.tool(**_TOOL_KW)
async def get_company_individual_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.Individual | None:
    """Fetch the full record for an individual (natural-person) PSC.

    Use when the ``get_company_psc_list`` entry has ``kind`` =
    ``individual-person-with-significant-control``. Returns name, date of birth
    (partial, per PSC protection rules), nationality, country of residence, and
    the nature of control held.
    """
    result = await ch_client.get_company_individual_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.Individual.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_individual_psc_beneficial_owner(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.IndividualBeneficialOwner | None:
    """Fetch the full record for an individual registrable beneficial owner (RBO).

    RBO entries apply to overseas entities within scope of the UK Register of
    Overseas Entities regime. Use when the list kind is
    ``individual-beneficial-owner``.
    """
    result = await ch_client.get_company_individual_psc_beneficial_owner(company_number, psc_id)
    if result is None:
        return None
    return types.psc.IndividualBeneficialOwner.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_corporate_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.CorporateEntity | None:
    """Fetch the full record for a corporate-entity PSC (a company exercising control).

    Use when the list kind is ``corporate-entity-person-with-significant-control``.
    Returns the controlling entity's registered name, registration number,
    jurisdiction, and nature of control.
    """
    result = await ch_client.get_company_corporate_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.CorporateEntity.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_corporate_psc_beneficial_owner(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.CorporateEntityBeneficialOwner | None:
    """Fetch the full record for a corporate registrable beneficial owner.

    Use when the list kind is ``corporate-entity-beneficial-owner``.
    """
    result = await ch_client.get_company_corporate_psc_beneficial_owner(company_number, psc_id)
    if result is None:
        return None
    return types.psc.CorporateEntityBeneficialOwner.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_legal_person_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.LegalPerson | None:
    """Fetch the full record for a legal-person PSC (a non-company legal entity).

    Covers entities such as trusts, foundations, or unincorporated associations
    with legal personality. Use when the list kind is
    ``legal-person-person-with-significant-control``.
    """
    result = await ch_client.get_company_legal_person_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.LegalPerson.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_legal_person_psc_beneficial_owner(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.LegalPersonBeneficialOwner | None:
    """Fetch the full record for a legal-person registrable beneficial owner.

    Use when the list kind is ``legal-person-beneficial-owner``.
    """
    result = await ch_client.get_company_legal_person_psc_beneficial_owner(company_number, psc_id)
    if result is None:
        return None
    return types.psc.LegalPersonBeneficialOwner.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_super_secure_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.SuperSecure | None:
    """Fetch the record for a super-secure PSC.

    "Super-secure" means the PSC's personal details are withheld from the public
    register because disclosure would put them at serious risk (domestic abuse,
    terrorism, etc.). Returns only the minimal publishable metadata. Use when
    the list kind is ``super-secure-person-with-significant-control``.
    """
    result = await ch_client.get_company_super_secure_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.SuperSecure.from_api_t(result)


@psc_mcp.tool(**_TOOL_KW)
async def get_company_super_secure_beneficial_owner_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.SuperSecureBeneficialOwner | None:
    """Fetch the record for a super-secure registrable beneficial owner.

    Use when the list kind is ``super-secure-beneficial-owner``. See
    ``get_company_super_secure_psc`` for notes on why details are withheld.
    """
    result = await ch_client.get_company_super_secure_beneficial_owner_psc(company_number, psc_id)
    if result is None:
        return None
    return types.psc.SuperSecureBeneficialOwner.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return psc_mcp
