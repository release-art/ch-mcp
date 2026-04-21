"""Reflections of FCA api fund types"""

import fca_api.types.markets as fca_market_types

from . import base


class RegulatedMarket(base.reflect_fca_api_t(fca_market_types.RegulatedMarket)):
    """Reflected RegulatedMarket model with conversion support"""
