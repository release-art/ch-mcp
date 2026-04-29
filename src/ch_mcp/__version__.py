from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


__version__ = "0.0.7"
cache_version = ".".join(__version__.split(".")[:2])  # "0.0"
