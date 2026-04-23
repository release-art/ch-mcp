"""Base reflection machinery for Companies House API response models."""

from __future__ import annotations

import types as _py_types
import typing
from typing import Self

import ch_api.types.shared
import pydantic
from pydantic_core import PydanticUndefined

from . import refs as _refs

ModelT = typing.TypeVar("ModelT", bound=pydantic.BaseModel)


class ReflectedChApiModel(pydantic.BaseModel):
    """Base class for reflected Companies House API models with conversion support."""

    # Subclasses set this to a ``BaseRefs`` subclass when they carry a ``refs``
    # field. ``from_api_t`` then extracts IDs from the source ``links`` block
    # and injects them into the validated payload.
    _refs_type: typing.ClassVar[type[_refs.BaseRefs] | None] = None

    @classmethod
    def from_api_t(cls, data: pydantic.BaseModel) -> Self:
        payload = data.model_dump(mode="python")
        if cls._refs_type is not None:
            # Prefer the live ``links`` attribute on the source instance over
            # the dumped dict — inherited/extra-allow fields survive dump()
            # inconsistently across pydantic configs, but direct attribute
            # access gives us everything.
            raw_links = getattr(data, "links", None)
            links_dict: typing.Mapping[str, typing.Any] | None = None
            if isinstance(raw_links, pydantic.BaseModel):
                links_dict = raw_links.model_dump(mode="python")
            elif isinstance(raw_links, typing.Mapping):
                links_dict = raw_links
            payload["refs"] = _refs.extract_refs(cls._refs_type, links_dict)
        return cls.model_validate(payload)


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
    exclude_names: tuple[str, ...] = ("etag",),
    *,
    refs_type: type[_refs.BaseRefs] | None = None,
) -> typing.Type[ReflectedChApiModel]:
    """Dynamically create a Pydantic model mirroring ``model_cls``.

    Fields are omitted when either:

    - their annotation is (or includes) a type in ``exclude_types`` — default
      drops ``shared.LinksSection`` HATEOAS blocks, which carry internal API
      resource URLs of no use to MCP clients; or
    - their name appears in ``exclude_names`` — default drops ``etag``, the
      optimistic-concurrency token used only by write endpoints.

    If ``refs_type`` is supplied, the generated model gains a ``refs`` field
    of that type. At ``from_api_t`` time, every URL in the source model's
    ``links`` block is scanned for embedded IDs (see :mod:`refs`) and the
    resulting ``*Refs`` instance is injected into the validated payload —
    giving MCP callers the IDs they need to chain tool calls without ever
    seeing the raw URLs.

    Nested ``pydantic.BaseModel`` field types are recursively reflected with
    the same exclusion policy, so the filters apply at every depth. Nested
    reflections do *not* inherit ``refs_type`` — only the top-level model
    opts in per call.
    """
    fields: dict[str, typing.Any] = {}
    for name, field in model_cls.model_fields.items():
        if name in exclude_names:
            continue
        if _annotation_contains_type(field.annotation, exclude_types):
            continue
        field_t: typing.Any = field.annotation
        if isinstance(field_t, type) and issubclass(field_t, pydantic.BaseModel):
            field_t = reflect_ch_api_t(field_t, exclude_types, exclude_names)
        if field.default is PydanticUndefined:
            fields[name] = (field_t, ...)
        else:
            fields[name] = (field_t, field.default)
    if refs_type is not None:
        fields["refs"] = (refs_type, ...)
    generated = pydantic.create_model(  # type: ignore[call-overload]
        f"{model_cls.__name__}Reflected",
        __base__=ReflectedChApiModel,
        **fields,
    )
    generated._refs_type = refs_type
    return generated
