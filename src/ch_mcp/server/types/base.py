"""Base reflection machinery for Companies House API response models."""

from __future__ import annotations

import types as _py_types
import typing
from typing import Self

import ch_api.types.shared
import pydantic
from pydantic_core import PydanticUndefined

ModelT = typing.TypeVar("ModelT", bound=pydantic.BaseModel)


class ReflectedChApiModel(pydantic.BaseModel):
    """Base class for reflected Companies House API models with conversion support."""

    @classmethod
    def from_api_t(cls, data: pydantic.BaseModel) -> Self:
        return cls.model_validate(data.model_dump(mode="python"))


def _annotation_contains_type(annotation: typing.Any, excluded: tuple[type, ...]) -> bool:
    """Return True if the given annotation resolves to (or includes) one of the excluded types.

    Unwraps ``typing.Annotated``, ``Optional``/``Union``, and ``X | None`` syntax.
    """
    if annotation is None or annotation is type(None):
        return False
    if isinstance(annotation, type) and issubclass(annotation, excluded):
        return True
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        inner, *_ = typing.get_args(annotation)
        return _annotation_contains_type(inner, excluded)
    if origin in (typing.Union, _py_types.UnionType):
        return any(_annotation_contains_type(arg, excluded) for arg in typing.get_args(annotation))
    return False


def reflect_ch_api_t(
    model_cls: typing.Type[ModelT],
    exclude_types: tuple[type, ...] = (ch_api.types.shared.LinksSection,),
) -> typing.Type[ReflectedChApiModel]:
    """Dynamically create a Pydantic model mirroring ``model_cls``.

    Fields whose annotation is (or includes) a type in ``exclude_types`` are
    omitted. Nested ``pydantic.BaseModel`` field types are recursively
    reflected with the same exclusion policy. By default this drops any
    ``shared.LinksSection`` field \u2014 those hold internal API resource URLs
    that are not useful to MCP clients.
    """
    fields: dict[str, tuple[typing.Any, typing.Any]] = {}
    for name, field in model_cls.model_fields.items():
        if _annotation_contains_type(field.annotation, exclude_types):
            continue
        field_t: typing.Any = field.annotation
        if isinstance(field_t, type) and issubclass(field_t, pydantic.BaseModel):
            field_t = reflect_ch_api_t(field_t, exclude_types)
        if field.default is PydanticUndefined:
            fields[name] = (field_t, ...)
        else:
            fields[name] = (field_t, field.default)
    return pydantic.create_model(
        f"{model_cls.__name__}Reflected",
        **fields,
        __base__=ReflectedChApiModel,
    )
