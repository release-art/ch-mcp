"""Reflected Persons-with-Significant-Control (PSC) types."""

import ch_api.types.public_data.psc as _psc

from . import base


class ListSummary(base.reflect_ch_api_t(_psc.ListSummary)):
    """Entry in the PSC list for a company."""


class Statement(base.reflect_ch_api_t(_psc.Statement)):
    """PSC statement recorded against a company."""


class Individual(base.reflect_ch_api_t(_psc.Individual)):
    """Individual person with significant control."""


class IndividualBeneficialOwner(base.reflect_ch_api_t(_psc.IndividualBeneficialOwner)):
    """Individual registrable beneficial owner."""


class CorporateEntity(base.reflect_ch_api_t(_psc.CorporateEntity)):
    """Corporate entity with significant control."""


class CorporateEntityBeneficialOwner(base.reflect_ch_api_t(_psc.CorporateEntityBeneficialOwner)):
    """Corporate registrable beneficial owner."""


class LegalPerson(base.reflect_ch_api_t(_psc.LegalPerson)):
    """Legal person with significant control."""


class LegalPersonBeneficialOwner(base.reflect_ch_api_t(_psc.LegalPersonBeneficialOwner)):
    """Legal person registrable beneficial owner."""


class SuperSecure(base.reflect_ch_api_t(_psc.SuperSecure)):
    """Super-secure person with significant control."""


class SuperSecureBeneficialOwner(base.reflect_ch_api_t(_psc.SuperSecureBeneficialOwner)):
    """Super-secure registrable beneficial owner."""
