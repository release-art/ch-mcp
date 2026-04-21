"""Reflections of FCA api fund types"""

import fca_api.types.search as fca_search_types

from . import base


class FirmSearchResult(base.reflect_fca_api_t(fca_search_types.FirmSearchResult)):
    """Reflected FirmSearchResult model with conversion support"""


class IndividualSearchResult(base.reflect_fca_api_t(fca_search_types.IndividualSearchResult)):
    """Reflected IndividualSearchResult model with conversion support"""


class FundSearchResult(base.reflect_fca_api_t(fca_search_types.FundSearchResult)):
    """Reflected FundSearchResult model with conversion support"""
