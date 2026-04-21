import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_get_regulated_markets(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_regulated_markets",
        arguments={},
    )
    assert tool_result is not None
    assert len(tool_result.data.items) > 0
    assert "ICE Futures Europe" in str(tool_result.data)
