"""MCP server for the UK FCA Financial Services Register.

A FastMCP server exposing the FCA Register via 25 read-only tools over HTTP
or stdio. See ``server.get_server()`` for the composed server and
``cli`` for the command-line entry point.
"""

from __future__ import annotations

import logging as std_logging

from . import (
    __version__,
    azure,
    cli,
    http,
    logging as fca_logging,
    server,
    settings,
    telemetry,
    uvcorn_app,
)

logger = std_logging.getLogger(__name__)
logging = fca_logging
version = __version__.__version__
