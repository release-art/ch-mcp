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


@pytest.mark.asyncio
async def test_get_document_metadata(mcp_client: Client[FastMCPTransport]):
    # A known filing document for company 09370755. The first run with a live
    # CH_API_API_KEY populates this fixture; subsequent runs replay from disk.
    filing_history = await mcp_client.call_tool(
        name="get_company_filing_history",
        arguments={"company_number": "09370755"},
    )
    items = filing_history.data.items  # type: ignore[union-attr]
    document_id = next(
        (item.refs.document_id for item in items if getattr(item.refs, "document_id", None)),
        None,
    )
    assert document_id, "fixture should contain at least one filing with a document_id"

    metadata = await mcp_client.call_tool(
        name="get_document_metadata",
        arguments={"document_id": document_id},
    )
    assert metadata is not None
    assert metadata.data.refs.document_id == document_id  # type: ignore[union-attr]


_SAMPLE_DOCUMENT_ID = "QbSample_Document_ID_AAAAAAAAAAAAAAAAAA"


@pytest.mark.asyncio
async def test_get_document_content(mcp_client: Client[FastMCPTransport]):
    # In HTTP transport mode (the default / test mode), the tool mints a
    # signed URL pointing at this server's own /documents/{token} route.
    # No bytes are fetched yet — that happens when the URL is hit.
    result = await mcp_client.call_tool(
        name="get_document_content",
        arguments={"document_id": _SAMPLE_DOCUMENT_ID, "content_type": "application/pdf"},
    )
    assert result is not None
    data = result.data
    assert data.document_id == _SAMPLE_DOCUMENT_ID
    assert data.content_type == "application/pdf"
    assert data.expires_in_seconds == 600
    assert data.url.startswith("http")
    assert "/documents/" in data.url
