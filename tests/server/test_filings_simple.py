import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_get_company_filing_history(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_filing_history",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_get_company_charges(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_charges",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_get_company_exemptions(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_exemptions",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None


@pytest.mark.asyncio
async def test_get_company_insolvency(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_company_insolvency",
        arguments={"company_number": "09370755"},
    )
    assert tool_result is not None
