"""Reflected company-level Companies House types."""

import ch_api.types.public_data.company_profile as _cp
import ch_api.types.public_data.company_registers as _cr
import ch_api.types.public_data.registered_office as _ro
import ch_api.types.public_data.uk_establishments as _uk

from . import base


class CompanyProfile(base.reflect_ch_api_t(_cp.CompanyProfile)):
    """Full profile of a UK company registered with Companies House."""


class RegisteredOfficeAddress(base.reflect_ch_api_t(_ro.RegisteredOfficeAddress)):
    """Registered office address of a company."""


class CompanyRegister(base.reflect_ch_api_t(_cr.CompanyRegister)):
    """The location and status of a company's statutory registers."""


class CompanyUKEstablishments(base.reflect_ch_api_t(_uk.CompanyUKEstablishments)):
    """UK establishments registered under an overseas company."""
