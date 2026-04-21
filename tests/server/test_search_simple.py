import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_search_frn(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="search_frn",
        arguments={
            "firm_name": "Liverpool Victoria",
        },
    )
    assert tool_result is not None
    assert "Liverpool Victoria Banking Services Limited" in str(tool_result.data)


@pytest.mark.asyncio
async def test_search_irn(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="search_irn",
        arguments={
            "individual_name": "John Smith",
        },
    )
    assert tool_result is not None
    assert "John Smith" in str(tool_result.data)


@pytest.mark.asyncio
async def test_search_prn(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="search_prn",
        arguments={
            "fund_name": "Vanguard",
        },
    )
    assert tool_result is not None
    assert "Vanguard" in str(tool_result.data)
