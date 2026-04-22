"""Lifespan-scoped container for shared runtime state."""

import dataclasses

import ch_api


@dataclasses.dataclass(slots=True)
class ChApp:
    """Holds the open ``ch_api`` client for the server's lifetime."""

    ch_api: ch_api.Client
