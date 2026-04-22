"""Reflected filings-related Companies House types (charges, filings, insolvency, exemptions)."""

import ch_api.types.public_data.charges as _ch
import ch_api.types.public_data.exemptions as _ex
import ch_api.types.public_data.filing_history as _fh
import ch_api.types.public_data.insolvency as _ins

from . import base


class ChargeList(base.reflect_ch_api_t(_ch.ChargeList)):
    """Charges (registered security interests) against a company."""


class ChargeDetails(base.reflect_ch_api_t(_ch.ChargeDetails)):
    """Detailed information about a single charge."""


class FilingHistoryItem(base.reflect_ch_api_t(_fh.FilingHistoryItem)):
    """Single item in a company's filing history."""


class CompanyInsolvency(base.reflect_ch_api_t(_ins.CompanyInsolvency)):
    """Insolvency cases recorded against a company."""


class CompanyExemptions(base.reflect_ch_api_t(_ex.CompanyExemptions)):
    """Exemptions granted to a company."""
