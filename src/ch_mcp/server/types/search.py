"""Reflected Companies House search result types."""

import ch_api.types.public_data.search as _search
import ch_api.types.public_data.search_companies as _sc

from . import base


class CompanySearchItem(base.reflect_ch_api_t(_search.CompanySearchItem)):
    """A single company hit in a Companies House search."""


class OfficerSearchItem(base.reflect_ch_api_t(_search.OfficerSearchItem)):
    """A single officer hit in a Companies House search."""


class DisqualifiedOfficerSearchItem(base.reflect_ch_api_t(_search.DisqualifiedOfficerSearchItem)):
    """A single disqualified-officer hit in a Companies House search."""


class AdvancedCompany(base.reflect_ch_api_t(_sc.AdvancedCompany)):
    """A company entry returned by the advanced company search endpoint."""


class AlphabeticalCompany(base.reflect_ch_api_t(_sc.AlphabeticalCompany)):
    """A company entry returned by the alphabetical company search endpoint."""


class DissolvedCompany(base.reflect_ch_api_t(_sc.DissolvedCompany)):
    """A dissolved company entry."""
