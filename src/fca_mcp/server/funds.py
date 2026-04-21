import logging
from typing import Annotated

import fastmcp
import fca_api
import pydantic
from mcp.types import ToolAnnotations

from . import deps, types

logger = logging.getLogger(__name__)
funds_mcp = fastmcp.FastMCP("search-funds", on_duplicate="error")

_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

PrnParam = Annotated[
    str,
    pydantic.Field(
        description=(
            "The Product Reference Number (PRN), a unique identifier assigned by the FCA"
            " to each registered fund. Obtain this by calling search_prn first."
        ),
    ),
]


@funds_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_fund(
    prn: PrnParam, fca_client: fca_api.async_api.Client = deps.FcaApiDep
) -> types.products.ProductDetails:
    """Retrieve detailed information about a specific FCA-registered investment fund.

    Use this tool when you have a Product Reference Number (PRN) and need the fund's full
    details, including its name, type, status, and management information. If you do not
    have a PRN, call search_prn first with the fund name. Returns core fund details
    only — use get_fund_subfunds for constituent sub-fund information, or get_fund_names
    for alternative names.
    """
    out = await fca_client.get_fund(prn)
    return types.products.ProductDetails.from_api_t(out)


@funds_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_fund_names(
    prn: PrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.products.ProductNameAlias]:
    """Retrieve all names and name aliases for a specific FCA-registered investment fund.

    Use this tool to find alternative, former, or marketing names a fund has used. Useful
    for verifying whether different names refer to the same fund entity. If you do not
    have a PRN, call search_prn first with the fund name.
    """
    out = await fca_client.get_fund_names(prn, next_page=next_page_token)
    return types.pagination.MultipageList[types.products.ProductNameAlias](
        items=[types.products.ProductNameAlias.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


@funds_mcp.tool(annotations=_TOOL_ANNOTATIONS)
async def get_fund_subfunds(
    prn: PrnParam,
    next_page_token: fca_api.types.pagination.NextPageToken | None = None,
    fca_client: fca_api.async_api.Client = deps.FcaApiDep,
) -> types.pagination.MultipageList[types.products.SubFundDetails]:
    """Retrieve all sub-funds within a specific FCA-registered umbrella fund.

    Sub-funds are distinct investment compartments within a larger fund structure, each
    with its own investment strategy and risk profile. Use this tool when you need to
    explore the components of an umbrella or multi-compartment fund. If you do not have
    a PRN, call search_prn first with the fund name.
    """
    out = await fca_client.get_fund_subfunds(prn, next_page=next_page_token)
    return types.pagination.MultipageList[types.products.SubFundDetails](
        items=[types.products.SubFundDetails.from_api_t(el) for el in out.data],
        pagination=types.pagination.PaginationInfo.from_api_t(out.pagination),
    )


def get_server() -> fastmcp.FastMCP:
    return funds_mcp
