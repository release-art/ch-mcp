"""Reflected Companies House search result types."""

import ch_api.types.public_data.search as _search
import ch_api.types.public_data.search_companies as _sc

from . import base, refs


class CompanySearchItem(base.reflect_ch_api_t(_search.CompanySearchItem, refs_type=refs.CompanySearchItemRefs)):
    """A single company hit in a Companies House search."""


class OfficerSearchItem(base.reflect_ch_api_t(_search.OfficerSearchItem, refs_type=refs.OfficerSearchItemRefs)):
    """A single officer hit in a Companies House search."""


class DisqualifiedOfficerSearchItem(
    base.reflect_ch_api_t(_search.DisqualifiedOfficerSearchItem, refs_type=refs.DisqualifiedOfficerSearchItemRefs)
):
    """A single disqualified-officer hit in a Companies House search."""


class AdvancedCompany(base.reflect_ch_api_t(_sc.AdvancedCompany, refs_type=refs.AdvancedCompanyRefs)):
    """A company entry returned by the advanced company search endpoint."""


class AlphabeticalCompany(base.reflect_ch_api_t(_sc.AlphabeticalCompany, refs_type=refs.AlphabeticalCompanyRefs)):
    """A company entry returned by the alphabetical company search endpoint."""


class DissolvedCompany(base.reflect_ch_api_t(_sc.DissolvedCompany, refs_type=refs.DissolvedCompanyRefs)):
    """A dissolved company entry."""
