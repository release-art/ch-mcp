import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_search_companies(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="search_companies",
        arguments={"query": "Tesco"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_search_officers(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="search_officers",
        arguments={"query": "Smith"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_search_disqualified_officers(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="search_disqualified_officers",
        arguments={"query": "Smith"},
    )
    assert tool_result is not None
