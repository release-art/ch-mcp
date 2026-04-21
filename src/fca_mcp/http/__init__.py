"""HTTP-only routes layered on top of the MCP server (interactive OAuth UI)."""

import fastmcp

from . import interactive


def mount_interactive_router(mcp: fastmcp.FastMCP) -> None:
    """Mount the interactive web UI routes at ``/interactive``.

    Only called when ``AUTH0_INTERACTIVE_CLIENT_ID`` is configured.
    """
    mcp.custom_route("/interactive/config", methods=["GET"], include_in_schema=False)(interactive.interactive_config)
    mcp.custom_route("/interactive", methods=["GET"], include_in_schema=False)(interactive.interactive_ui)
