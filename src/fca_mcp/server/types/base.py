import typing
from typing import Self

import fca_api.types
import pydantic
from pydantic_core import PydanticUndefined

ModelT = typing.TypeVar("ModelT", bound=pydantic.BaseModel)


class ReflectedFcaApiModelT(pydantic.BaseModel, typing.Generic[ModelT]):
    """Base class for reflected FCA API models with conversion support."""

    @classmethod
    def from_api_t(cls, data: ModelT) -> Self:
        return cls.model_validate(data.model_dump(mode="python"))  # type: ignore[return-value]


def reflect_fca_api_t(
    model_cls: typing.Type[ModelT],
    exclude_fields: typing.Tuple[fca_api.types.annotations.FcaApiField, ...] = (
        fca_api.types.annotations.FcaApiField.InternalUrl,
    ),
) -> typing.Type[ReflectedFcaApiModelT[ModelT]]:
    """
    Dynamically creates a new Pydantic model class with all fields from the input model,
    except those marked by fca_api as being of type HttpUrl.
    """
    fields = {}
    for name, field in model_cls.model_fields.items():
        field_excluded = False
        field_t = field.annotation
        if field.metadata:
            for metadata_el in field.metadata:
                if isinstance(metadata_el, fca_api.types.annotations.FcaApiFieldInfo):
                    # Found fca-api metadata element, check if it's in the exclude list
                    if metadata_el.marks.intersection(exclude_fields):
                        field_excluded = True
                        break
        if field_excluded:
            continue
        # Apply same logic for all child models
        if isinstance(field.annotation, type) and issubclass(field.annotation, pydantic.BaseModel):
            # This is a child model, we need to reflect it as well
            field_t = reflect_fca_api_t(field.annotation, exclude_fields)
        # Handle required and default values
        if field.default is PydanticUndefined:
            fields[name] = (field_t, ...)
        else:
            fields[name] = (field_t, field.default)
    return pydantic.create_model(
        f"{model_cls.__name__}Reflected",
        **fields,
        __base__=ReflectedFcaApiModelT[ModelT],
    )
