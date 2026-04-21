"""Lifespan-scoped container for shared runtime state."""

import dataclasses

import fca_api


@dataclasses.dataclass(slots=True)
class FcaApp:
    """Holds the open ``fca_api`` client for the server's lifetime."""

    fca_api: fca_api.async_api.Client
