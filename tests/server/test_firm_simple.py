import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest.mark.asyncio
async def test_tools(mcp_client: Client[FastMCPTransport]):
    tools = await mcp_client.list_tools()
    assert len(tools) > 1


@pytest.mark.asyncio
async def test_get_firm(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm",
        arguments={
            "frn": "482551",
        },
    )
    assert tool_result is not None
    assert "Barclays Capital" in str(tool_result.data)
    assert "482551" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_names(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_names",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "Barclays Bank UK PLC" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_addresses(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_addresses",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "1 Churchill Place" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_individuals(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_individuals",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "Stephen John Weston" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_permissions(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_permissions",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "Making arrangements with a view to transactions in investments" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_requirements(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_requirements",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "EC2R 6DA has decided to take the following action" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_requirement_investment_types(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_requirement_investment_types",
        arguments={
            "frn": "759676",
            "req_ref": "OR-0215096",
        },
    )
    assert tool_result is not None
    assert "items=[]" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_regulators(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_regulators",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "Financial Conduct Authority" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_passports(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_passports",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "GIBRALTAR" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_passport_permissions(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_passport_permissions",
        arguments={
            "frn": "759676",
            "country": "GIBRALTAR",
        },
    )
    assert tool_result is not None
    assert "GIBRALTAR" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_waivers(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_waivers",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "CRR Ar 113(6)" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_exclusions(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_exclusions",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "items=[]" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_disciplinary_history(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_disciplinary_history",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "The reason for this action is" in str(tool_result.data)


@pytest.mark.asyncio
async def test_get_firm_appointed_representatives(mcp_client: Client[FastMCPTransport]):
    tool_result = await mcp_client.call_tool(
        name="get_firm_appointed_representatives",
        arguments={
            "frn": "759676",
        },
    )
    assert tool_result is not None
    assert "Tesco Stores Limited" in str(tool_result.data)
