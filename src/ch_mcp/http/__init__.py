"""HTTP-only routes layered on top of the MCP server.

Each route module exports a ``mount_<name>_router(mcp)`` function that owns
its own ``custom_route`` registration. The HTTP app factory in
:mod:`ch_mcp.uvcorn_app` just chains the mounts it wants — there is no
shared imperative registration blob. Modules whose routes are conditional
on config (e.g. the interactive OAuth UI) decide whether to mount
themselves at call time.
"""

from . import documents, health, interactive, landing
from .documents import mount_documents_router
from .health import mount_health_router
from .interactive import mount_interactive_router
from .landing import mount_landing_router

__all__ = [
    "documents",
    "health",
    "interactive",
    "landing",
    "mount_documents_router",
    "mount_health_router",
    "mount_interactive_router",
    "mount_landing_router",
]
