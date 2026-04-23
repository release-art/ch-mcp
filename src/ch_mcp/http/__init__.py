"""HTTP-only routes layered on top of the MCP server.

Each route module exports a ``mount_<name>_router(mcp)`` function that owns
its own ``custom_route`` registration. The HTTP app factory in
:mod:`ch_mcp.uvcorn_app` just chains the mounts it wants — there is no
shared imperative registration blob.
"""

from . import documents, health, landing
from .documents import mount_documents_router
from .health import mount_health_router
from .landing import mount_landing_router

__all__ = [
    "documents",
    "health",
    "landing",
    "mount_documents_router",
    "mount_health_router",
    "mount_landing_router",
]
