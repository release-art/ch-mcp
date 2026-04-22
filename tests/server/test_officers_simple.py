import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_get_officer_list(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_officer_list",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_get_officer_appointments(mcp_client: Client[FastMCPTransport]):
    # Use a well-known long-serving officer ID; tests seed the cache on first run.
    tool_result = await mcp_client.call_tool(
        name="get_officer_appointments",
        arguments={"officer_id": "MCM0Z5x9Lw7NS8cNnD5VGc_bXzE"},
    )
    assert tool_result is not None
