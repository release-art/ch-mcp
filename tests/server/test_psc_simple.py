import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_get_company_psc_list(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_psc_list",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_get_company_psc_statements(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_psc_statements",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None
