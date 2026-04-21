"""Test for server type base"""
# ruff: noqa: N806

import typing

import fca_api.types as fca_api_types
import pydantic

import fca_mcp.server.types.base as server_type_base


class TestReflect:
    def test_simple(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str

        ModelB = server_type_base.reflect_fca_api_t(ModelA)
        assert ModelA.model_json_schema() == (ModelB.model_json_schema() | {"title": "ModelA"})

    def test_exclude_with_pydantic_field(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            c: typing.Annotated[
                str,
                pydantic.Field(),
                fca_api_types.annotations.FcaApiFieldInfo(marks={fca_api_types.annotations.FcaApiField.InternalUrl}),
            ]

        ModelB = server_type_base.reflect_fca_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "b" in ModelB.model_fields
        assert "c" not in ModelB.model_fields

    def test_exclude_nullable_with_pydantic_field(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            c: typing.Annotated[
                pydantic.HttpUrl | None,
                pydantic.Field(
                    description="The URL of the firm's record in the FCA register.",
                ),
                fca_api_types.annotations.FcaApiFieldInfo(marks=[fca_api_types.annotations.FcaApiField.InternalUrl]),
            ]

        ModelB = server_type_base.reflect_fca_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "b" in ModelB.model_fields
        assert "c" not in ModelB.model_fields

    def test_exclude_without_pydantic_field(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            c: typing.Annotated[
                str,
                # pydantic.Field(),
                fca_api_types.annotations.FcaApiFieldInfo(marks={fca_api_types.annotations.FcaApiField.InternalUrl}),
            ]

        ModelB = server_type_base.reflect_fca_api_t(ModelA)
        assert "a" in ModelB.model_fields
        assert "b" in ModelB.model_fields
        assert "c" not in ModelB.model_fields

    def test_exclude_in_children(self):
        class ModelA(pydantic.BaseModel):
            a: int
            b: str
            c: typing.Annotated[
                str,
                pydantic.Field(),
                fca_api_types.annotations.FcaApiFieldInfo(marks={fca_api_types.annotations.FcaApiField.InternalUrl}),
            ]

        class ModelC(pydantic.BaseModel):
            x: int
            y: ModelA

        ModelD = server_type_base.reflect_fca_api_t(ModelC)
        assert "x" in ModelD.model_fields
        assert "y" in ModelD.model_fields
        assert "a" in ModelD.model_fields["y"].annotation.model_fields
        assert "b" in ModelD.model_fields["y"].annotation.model_fields
        assert "c" not in ModelD.model_fields["y"].annotation.model_fields
