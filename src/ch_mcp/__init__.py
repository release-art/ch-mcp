"""MCP server for the UK Companies House API.

A FastMCP server exposing the UK Companies House API via read-only tools
over HTTP or stdio. See ``server.get_server()`` for the composed server
and ``cli`` for the command-line entry point.
"""

from __future__ import annotations

import logging as std_logging

from . import (
    __version__,
    azure,
    cli,
    http,
    logging as ch_logging,
    server,
    settings,
    telemetry,
    uvcorn_app,
)

logger = std_logging.getLogger(__name__)
logging = ch_logging
version = __version__.__version__
