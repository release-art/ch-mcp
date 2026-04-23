"""Reflected filings-related Companies House types (charges, filings, insolvency, exemptions, documents)."""

import ch_api.types.public_data.charges as _ch
import ch_api.types.public_data.documents as _doc
import ch_api.types.public_data.exemptions as _ex
import ch_api.types.public_data.filing_history as _fh
import ch_api.types.public_data.insolvency as _ins

from . import base, refs


# ChargeList is a top-level collection wrapper; its items each carry their own
# refs, so the wrapper itself doesn't need one.
class ChargeList(base.reflect_ch_api_t(_ch.ChargeList)):
    """Charges (registered security interests) against a company."""


class ChargeDetails(base.reflect_ch_api_t(_ch.ChargeDetails, refs_type=refs.ChargeDetailsRefs)):
    """Detailed information about a single charge."""


class FilingHistoryItem(base.reflect_ch_api_t(_fh.FilingHistoryItem, refs_type=refs.FilingHistoryItemRefs)):
    """Single item in a company's filing history."""


class CompanyInsolvency(base.reflect_ch_api_t(_ins.CompanyInsolvency, refs_type=refs.CompanyInsolvencyRefs)):
    """Insolvency cases recorded against a company."""


class CompanyExemptions(base.reflect_ch_api_t(_ex.CompanyExemptions, refs_type=refs.CompanyExemptionsRefs)):
    """Exemptions granted to a company."""


class DocumentMetadata(base.reflect_ch_api_t(_doc.DocumentMetadata, refs_type=refs.DocumentMetadataRefs)):
    """Metadata for a single filed document on the Companies House Document API."""
