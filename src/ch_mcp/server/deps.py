"""Companies House API dependencies."""

from __future__ import annotations

import logging

import ch_api
import fastmcp
from fastmcp.dependencies import CurrentContext, Depends

from . import app

logger = logging.getLogger(__name__)

_current_context = CurrentContext()


def get_ch_app(ctx: fastmcp.Context = _current_context) -> app.ChApp:
    """Pull the ``ChApp`` container out of the current lifespan context."""
    return ctx.lifespan_context["ch_app"]


_ch_app_dep = Depends(get_ch_app)


def get_ch_api(ch_app=_ch_app_dep) -> ch_api.Client:
    """Yield the shared ``ch_api`` async client for a tool invocation."""
    return ch_app.ch_api


ChApiDep = Depends(get_ch_api)
