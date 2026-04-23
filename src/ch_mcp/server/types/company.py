"""Reflected company-level Companies House types."""

import ch_api.types.public_data.company_profile as _cp
import ch_api.types.public_data.company_registers as _cr
import ch_api.types.public_data.uk_establishments as _uk

from . import base, refs


class CompanyProfile(base.reflect_ch_api_t(_cp.CompanyProfile, refs_type=refs.CompanyProfileRefs)):
    """Full profile of a UK company registered with Companies House."""


class CompanyRegister(base.reflect_ch_api_t(_cr.CompanyRegister, refs_type=refs.CompanyRegisterRefs)):
    """The location and status of a company's statutory registers."""


class CompanyUKEstablishments(
    base.reflect_ch_api_t(_uk.CompanyUKEstablishments, refs_type=refs.CompanyUKEstablishmentsRefs)
):
    """UK establishments registered under an overseas company."""
