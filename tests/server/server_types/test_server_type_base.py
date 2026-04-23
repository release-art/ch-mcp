"""Tests for the ch_mcp type reflection layer."""
# ruff: noqa: N806

import typing

import ch_api.types.shared
import pydantic

import ch_mcp.server.types.base as server_type_base
from ch_mcp.server.types import refs as server_refs


class TestReflect:
    def test_simple(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str

        ModelB = server_type_base.reflect_ch_api_t(ModelA)
        assert ModelA.model_json_schema() == (ModelB.model_json_schema() | {"title": "ModelA"})

    def test_exclude_links_section(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            links: ch_api.types.shared.LinksSection

        ModelB = server_type_base.reflect_ch_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "b" in ModelB.model_fields
        assert "links" not in ModelB.model_fields

    def test_exclude_optional_links_section(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            links: ch_api.types.shared.LinksSection | None = None

        ModelB = server_type_base.reflect_ch_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "b" in ModelB.model_fields
        assert "links" not in ModelB.model_fields

    def test_exclude_annotated_links_section(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            links: typing.Annotated[
                ch_api.types.shared.LinksSection,
                pydantic.Field(description="HATEOAS links to related resources."),
            ]

        ModelB = server_type_base.reflect_ch_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "b" in ModelB.model_fields
        assert "links" not in ModelB.model_fields

    def test_exclude_in_children(self):
        class ModelA(pydantic.BaseModel):
            a: int
            links: ch_api.types.shared.LinksSection | None = None

        class ModelC(pydantic.BaseModel):
            x: int
            y: ModelA

        ModelD = server_type_base.reflect_ch_api_t(ModelC)
        assert "x" in ModelD.model_fields
        assert "y" in ModelD.model_fields
        reflected_y = ModelD.model_fields["y"].annotation
        assert "a" in reflected_y.model_fields
        assert "links" not in reflected_y.model_fields

    def test_exclude_etag_by_name(self):
        class ModelA(pydantic.BaseModel):
            a: int
            etag: str

        ModelB = server_type_base.reflect_ch_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "etag" not in ModelB.model_fields

    def test_exclude_etag_in_nested(self):
        class Inner(pydantic.BaseModel):
            b: int
            etag: str | None = None

        class Outer(pydantic.BaseModel):
            etag: str | None = None
            inner: Inner

        Reflected = server_type_base.reflect_ch_api_t(Outer)
        assert "etag" not in Reflected.model_fields
        assert "inner" in Reflected.model_fields
        assert "etag" not in Reflected.model_fields["inner"].annotation.model_fields
        assert "b" in Reflected.model_fields["inner"].annotation.model_fields

    def test_refs_type_populated_from_links(self):
        """Reflection with refs_type extracts IDs from the source ``links`` block."""

        class Source(pydantic.BaseModel):
            x: int
            # Minimal stand-in for a ch_api model with a links block. LinksSection
            # has extra="allow", so arbitrary string URLs stored as extras survive
            # model_dump and are visible to the refs extractor.
            links: ch_api.types.shared.LinksSection

        Reflected = server_type_base.reflect_ch_api_t(Source, refs_type=server_refs.FilingHistoryItemRefs)

        assert "refs" in Reflected.model_fields
        assert "links" not in Reflected.model_fields  # still stripped

        src = Source(
            x=7,
            links=ch_api.types.shared.LinksSection.model_validate(
                {
                    "self": "/company/09370755/filing-history/txn-42",
                    "document_metadata": "/document/DOC_ID",
                }
            ),
        )
        reflected = Reflected.from_api_t(src)
        assert reflected.refs.company_number == "09370755"  # type: ignore[attr-defined]
        assert reflected.refs.transaction_id == "txn-42"  # type: ignore[attr-defined]
        assert reflected.refs.document_id == "DOC_ID"  # type: ignore[attr-defined]
