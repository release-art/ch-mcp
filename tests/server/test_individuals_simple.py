import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_get_individual(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_individual",
        arguments={
            "irn": "BXK69703",
        },
    )
    assert tool_result is not None
    assert "Bob Keijzers" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_individual_controlled_functions(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_individual_controlled_functions",
        arguments={
            "irn": "BXK69703",
        },
    )
    assert tool_result is not None
    assert len(tool_result.data.items) > 0
    assert "[FCA CF] Client dealing" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_individual_disciplinary_history(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_individual_disciplinary_history",
        arguments={
            "irn": "NPD01015",
        },
    )
    assert tool_result is not None
    assert len(tool_result.data.items) > 0
    assert "Final Notice" in str(tool_result.data)
