"""Reflected Persons-with-Significant-Control (PSC) types."""

from typing import Annotated, Union

import ch_api.types.public_data.psc as _psc
import pydantic

from . import base, refs


class ListSummary(base.reflect_ch_api_t(_psc.ListSummary, refs_type=refs.PscListItemRefs)):
    """Entry in the PSC list for a company."""


class Statement(base.reflect_ch_api_t(_psc.Statement, refs_type=refs.PscStatementRefs)):
    """PSC statement recorded against a company."""


class Individual(base.reflect_ch_api_t(_psc.Individual, refs_type=refs.PscRecordRefs)):
    """Individual person with significant control."""


class IndividualBeneficialOwner(
    base.reflect_ch_api_t(_psc.IndividualBeneficialOwner, refs_type=refs.PscRecordRefs)
):
    """Individual registrable beneficial owner."""


class CorporateEntity(base.reflect_ch_api_t(_psc.CorporateEntity, refs_type=refs.PscRecordRefs)):
    """Corporate entity with significant control."""


class CorporateEntityBeneficialOwner(
    base.reflect_ch_api_t(_psc.CorporateEntityBeneficialOwner, refs_type=refs.PscRecordRefs)
):
    """Corporate registrable beneficial owner."""


class LegalPerson(base.reflect_ch_api_t(_psc.LegalPerson, refs_type=refs.PscRecordRefs)):
    """Legal person with significant control."""


class LegalPersonBeneficialOwner(
    base.reflect_ch_api_t(_psc.LegalPersonBeneficialOwner, refs_type=refs.PscRecordRefs)
):
    """Legal person registrable beneficial owner."""


class SuperSecure(base.reflect_ch_api_t(_psc.SuperSecure, refs_type=refs.PscRecordRefs)):
    """Super-secure person with significant control."""


class SuperSecureBeneficialOwner(
    base.reflect_ch_api_t(_psc.SuperSecureBeneficialOwner, refs_type=refs.PscRecordRefs)
):
    """Super-secure registrable beneficial owner."""


#: Discriminated union of every concrete PSC record type. Each variant declares
#: a distinct ``kind`` literal, so pydantic can statically narrow responses and
#: MCP clients see a tagged union in the output schema.
PscRecord = Annotated[
    Union[
        Individual,
        IndividualBeneficialOwner,
        CorporateEntity,
        CorporateEntityBeneficialOwner,
        LegalPerson,
        LegalPersonBeneficialOwner,
        SuperSecure,
        SuperSecureBeneficialOwner,
    ],
    pydantic.Field(discriminator="kind"),
]
