"""Reflections of FCA api fund types"""

import fca_api.types.products as fca_product_types

from . import base


class ProductDetails(base.reflect_fca_api_t(fca_product_types.ProductDetails)):
    """Reflected ProductDetails model with conversion support"""


class ProductNameAlias(base.reflect_fca_api_t(fca_product_types.ProductNameAlias)):
    """Reflected ProductNameAlias model with conversion support"""


class SubFundDetails(base.reflect_fca_api_t(fca_product_types.SubFundDetails)):
    """Reflected SubFundDetails model with conversion support"""
