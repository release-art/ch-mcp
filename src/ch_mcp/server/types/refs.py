"""Extracted resource IDs (``refs``) attached to reflected Companies House responses.

Every Companies House response carries a ``links`` section that embeds the IDs
of related resources in the URL tail (e.g. ``/company/09370755/charges/abc``).
This module:

1. Parses those URLs into a dict of named captures via :func:`parse_url_ids`.
2. Declares a small per-resource ``*Refs`` pydantic model for each reflected
   MCP response type, listing exactly which captured IDs that response is
   expected to expose.
3. Provides :func:`extract_refs` which runs the parser over every URL in a
   raw ``links`` dict, unions the captures, and validates them into the
   requested ``*Refs`` model.

The reflected response models (see :mod:`ch_mcp.server.types.base`) embed the
resulting refs as a ``refs: *Refs`` field, replacing the stripped ``links``
block so MCP callers can chain tool calls without parsing URLs themselves.
"""

from __future__ import annotations

import re
import typing

import pydantic

# ---------------------------------------------------------------------------
# URL parser
# ---------------------------------------------------------------------------

# Each pattern carries one or more named captures. All patterns are matched
# against every URL; the union of captures that fired becomes the ID dict.
# Patterns are non-anchored — they match wherever they appear in the URL so
# that partial paths and fully-qualified URLs behave the same way.
_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Company number — the parent of nearly every company-scoped URL.
    re.compile(r"/company/(?P<company_number>[A-Za-z0-9]{1,10})(?:/|$)"),
    # Charge: /company/{cn}/charges/{charge_id}
    re.compile(r"/charges/(?P<charge_id>[^/?]+)"),
    # Officer appointment on a company: /company/{cn}/appointments/{appointment_id}
    re.compile(r"/company/[^/]+/appointments/(?P<appointment_id>[^/?]+)"),
    # Filing history item: /company/{cn}/filing-history/{transaction_id}
    re.compile(r"/filing-history/(?P<transaction_id>[^/?]+)"),
    # PSC record: /company/{cn}/persons-with-significant-control/{url_kind}/{psc_id}
    re.compile(
        r"/persons-with-significant-control/"
        r"(?P<psc_url_kind>[^/]+)/(?P<psc_id>[^/?]+)"
    ),
    # PSC statement: /company/{cn}/persons-with-significant-control-statements/{statement_id}
    re.compile(r"/persons-with-significant-control-statements/(?P<psc_statement_id>[^/?]+)"),
    # Officer's global appointments list: /officers/{officer_id}/appointments
    # or the disqualified officer form: /disqualified-officers/(natural|corporate)/{officer_id}
    re.compile(r"/officers/(?P<officer_id>[^/?]+)(?:/|$)"),
    re.compile(
        r"/disqualified-officers/(?P<disqualification_kind>natural|corporate)"
        r"/(?P<officer_id_disq>[^/?]+)"
    ),
    # Document: /document/{document_id}(/content)?  (hosted on document-api.*)
    re.compile(r"/document/(?P<document_id>[^/?]+)"),
)


def parse_url_ids(url: str) -> dict[str, str]:
    """Extract every known ID from a Companies House URL.

    Returns a dict with one entry per named-capture that matched. Unmatched
    patterns contribute nothing. Normalises ``officer_id_disq`` into
    ``officer_id`` so callers always see a single key regardless of which
    endpoint the URL points at.
    """
    if not url:
        return {}
    found: dict[str, str] = {}
    for pattern in _URL_PATTERNS:
        m = pattern.search(url)
        if m is None:
            continue
        for key, value in m.groupdict().items():
            if value is not None:
                found[key] = value
    if "officer_id_disq" in found and "officer_id" not in found:
        found["officer_id"] = found.pop("officer_id_disq")
    else:
        found.pop("officer_id_disq", None)
    return found


def _collect_refs(raw_links: typing.Mapping[str, typing.Any] | None) -> dict[str, str]:
    """Walk a ``links`` dict, parse every URL-valued field, union the captures."""
    if not raw_links:
        return {}
    collected: dict[str, str] = {}
    for value in raw_links.values():
        if isinstance(value, str):
            collected.update(parse_url_ids(value))
    return collected


_RefsT = typing.TypeVar("_RefsT", bound="BaseRefs")


class BaseRefs(pydantic.BaseModel):
    """Base for all per-resource refs models — frozen, extras ignored."""

    model_config = pydantic.ConfigDict(frozen=True, extra="ignore")


def extract_refs(refs_type: type[_RefsT], raw_links: typing.Mapping[str, typing.Any] | None) -> _RefsT:
    """Build a ``*Refs`` instance from a raw links mapping.

    Every URL in ``raw_links`` is scanned; the union of captured IDs is fed to
    ``refs_type.model_validate(...)``. Optional ``| None`` fields stay ``None``
    when the corresponding anchor isn't present; required fields raise loudly
    when their anchor is missing (fail-fast for bugs in the regex table or
    in the source response).
    """
    collected = _collect_refs(raw_links)
    return refs_type.model_validate(collected)


# ---------------------------------------------------------------------------
# Per-resource refs models
# ---------------------------------------------------------------------------


class CompanyProfileRefs(BaseRefs):
    """IDs extracted from a ``CompanyProfile.links`` block."""

    company_number: str


class CompanyRegisterRefs(BaseRefs):
    """IDs extracted from a ``CompanyRegister.links`` block."""

    company_number: str


class CompanyUKEstablishmentsRefs(BaseRefs):
    """IDs extracted from a ``CompanyUKEstablishments.links`` block."""

    company_number: str


class CompanyExemptionsRefs(BaseRefs):
    """IDs extracted from a ``CompanyExemptions.links`` block."""

    company_number: str


class CompanyInsolvencyRefs(BaseRefs):
    """IDs extracted from a ``CompanyInsolvency.links`` block."""

    company_number: str


class OfficerListItemRefs(BaseRefs):
    """Refs for an item in the per-company officer list.

    ``self`` points at ``/company/{cn}/appointments/{appointment_id}``;
    ``officer.appointments`` (when present) points at
    ``/officers/{officer_id}/appointments`` — giving the caller both the
    company-scoped appointment ID and the officer's global ID.
    """

    company_number: str
    appointment_id: str
    officer_id: str | None = None


class OfficerAppointmentItemRefs(BaseRefs):
    """Refs for an entry in an officer's global appointments list.

    The item's ``self`` link gives back the company number and the
    company-scoped appointment ID.
    """

    company_number: str
    appointment_id: str


class DisqualificationRefs(BaseRefs):
    """IDs for a disqualification record."""

    officer_id: str


class ChargeSummaryRefs(BaseRefs):
    """Refs for a charge entry inside a ``ChargeList``."""

    company_number: str
    charge_id: str


class ChargeDetailsRefs(BaseRefs):
    """Refs for a single-charge detail response."""

    company_number: str
    charge_id: str


class FilingHistoryItemRefs(BaseRefs):
    """Refs for a filing-history item.

    ``document_id`` is populated when the filing has an associated
    downloadable document (``links.document_metadata`` present).
    """

    company_number: str
    transaction_id: str
    document_id: str | None = None


class PscListItemRefs(BaseRefs):
    """Refs for an entry in a company's PSC list."""

    company_number: str
    psc_id: str


class PscRecordRefs(BaseRefs):
    """Refs for a concrete PSC record."""

    company_number: str
    psc_id: str


class PscStatementRefs(BaseRefs):
    """Refs for a PSC statement."""

    company_number: str
    psc_statement_id: str


class DocumentMetadataRefs(BaseRefs):
    """Refs for a document metadata response."""

    document_id: str


class CompanySearchItemRefs(BaseRefs):
    """Refs for a company-search hit."""

    company_number: str


class OfficerSearchItemRefs(BaseRefs):
    """Refs for an officer-search hit."""

    officer_id: str


class DisqualifiedOfficerSearchItemRefs(BaseRefs):
    """Refs for a disqualified-officer search hit."""

    officer_id: str


class AdvancedCompanyRefs(BaseRefs):
    """Refs for an advanced-search company hit."""

    company_number: str


class AlphabeticalCompanyRefs(BaseRefs):
    """Refs for an alphabetical-search company hit."""

    company_number: str


class DissolvedCompanyRefs(BaseRefs):
    """Refs for a dissolved-company search hit."""

    company_number: str
