import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_tools(mcp_client: Client[FastMCPTransport]):
    tools = await mcp_client.list_tools()
    assert len(tools) > 1


@pytest.mark.asyncio
async def test_get_company_profile(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_profile",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None
    assert "09370755" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_company_registers(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_registers",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None
