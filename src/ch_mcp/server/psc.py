"""Persons with Significant Control (PSC) tools.

Companies House records five kinds of PSC, each with a "beneficial owner" variant:

- **individual** — a natural person exercising control.
- **corporate-entity** — a registered company exercising control.
- **legal-person** — a non-company legal entity (e.g. a trust, foundation).
- **super-secure** — a person whose details are withheld for safety.

Call ``get_company_psc_list`` first to enumerate a company's PSCs. Each item
carries a ``kind`` discriminator literal — pass that value straight into
``get_company_psc`` to fetch the full record. The response's own ``kind``
field lets MCP clients statically pick the right variant from the returned
discriminated union.
"""

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

PscKindParam = Annotated[
    Literal[
        "individual-person-with-significant-control",
        "individual-beneficial-owner",
        "corporate-entity-person-with-significant-control",
        "corporate-entity-beneficial-owner",
        "legal-person-person-with-significant-control",
        "legal-person-beneficial-owner",
        "super-secure-person-with-significant-control",
        "super-secure-beneficial-owner",
    ],
    pydantic.Field(
        description=(
            "The kind of PSC to fetch. Copy the value straight from the ``kind``"
            " field of the corresponding ``get_company_psc_list`` item — it is"
            " one of the eight literal values listed."
        ),
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


# Dispatch table: maps each ``kind`` literal to (ch_api method name, reflected response type).
_PSC_DISPATCH: dict[str, tuple[str, type[types.base.ReflectedChApiModel]]] = {
    "individual-person-with-significant-control": (
        "get_company_individual_psc",
        types.psc.Individual,
    ),
    "individual-beneficial-owner": (
        "get_company_individual_psc_beneficial_owner",
        types.psc.IndividualBeneficialOwner,
    ),
    "corporate-entity-person-with-significant-control": (
        "get_company_corporate_psc",
        types.psc.CorporateEntity,
    ),
    "corporate-entity-beneficial-owner": (
        "get_company_corporate_psc_beneficial_owner",
        types.psc.CorporateEntityBeneficialOwner,
    ),
    "legal-person-person-with-significant-control": (
        "get_company_legal_person_psc",
        types.psc.LegalPerson,
    ),
    "legal-person-beneficial-owner": (
        "get_company_legal_person_psc_beneficial_owner",
        types.psc.LegalPersonBeneficialOwner,
    ),
    "super-secure-person-with-significant-control": (
        "get_company_super_secure_psc",
        types.psc.SuperSecure,
    ),
    "super-secure-beneficial-owner": (
        "get_company_super_secure_beneficial_owner_psc",
        types.psc.SuperSecureBeneficialOwner,
    ),
}


@psc_mcp.tool(**_TOOL_KW)
async def get_company_psc_list(
    company_number: CompanyNumberParam,
    next_page_token: _NextPageParam = None,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.pagination.MultipageList[types.psc.ListSummary]:
    """List the persons with significant control (PSCs) declared for a company.

    PSCs are the individuals or entities that ultimately own or control the
    company (typically >25% of shares, >25% of voting rights, or right to appoint
    directors). Each entry's ``kind`` field indicates the PSC variant — pass
    that exact value as the ``kind`` argument to ``get_company_psc`` to fetch
    the full record.
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
async def get_company_psc(
    company_number: CompanyNumberParam,
    psc_id: PscIdParam,
    kind: PscKindParam,
    ch_client: ch_api.Client = deps.ChApiDep,
) -> types.psc.PscRecord | None:
    """Fetch the full record for a single person with significant control (PSC).

    This single tool covers every PSC variant (individual, corporate-entity,
    legal-person, super-secure, plus their beneficial-owner counterparts).
    Dispatch is driven by the ``kind`` argument — **copy it straight from the**
    ``kind`` **field of the corresponding** ``get_company_psc_list`` **item**;
    do not invent or translate the value.

    The response is a discriminated union keyed on the same ``kind`` field, so
    MCP clients can statically narrow to the right concrete variant. Returns
    ``None`` if no PSC exists at the given ``(company_number, psc_id)`` pair
    for that ``kind``.

    Notes on specific kinds:

    - ``super-secure-*`` — details are suppressed for safety; only the minimal
      publishable metadata is returned.
    - ``*-beneficial-owner`` — used for overseas entities under the UK Register
      of Overseas Entities regime.
    """
    method_name, result_type = _PSC_DISPATCH[kind]
    result = await getattr(ch_client, method_name)(company_number, psc_id)
    if result is None:
        return None
    return result_type.from_api_t(result)


def get_server() -> fastmcp.FastMCP:
    return psc_mcp
