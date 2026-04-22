"""Tests for the ch_mcp type reflection layer."""
# ruff: noqa: N806

import typing

import ch_api.types.shared
import pydantic

import ch_mcp.server.types.base as server_type_base


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
