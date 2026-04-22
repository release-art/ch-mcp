import typing

import ch_api.types.pagination.types as ch_pagination
import pydantic

T = typing.TypeVar("T")


class PaginationInfo(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    has_next: bool = pydantic.Field(description="True if more results are available beyond this page.")
    next_page: typing.Optional[ch_pagination.NextPageToken] = pydantic.Field(
        default=None,
        description="Cursor to pass to the same endpoint to fetch the next page. None when has_next is False.",
    )
    total_size: typing.Optional[int] = pydantic.Field(
        default=None,
        description=(
            "Estimated total number of items in the collection as reported by the"
            " Companies House API. May be approximate."
        ),
    )

    @classmethod
    def from_api_t(cls, pagination: ch_pagination.PaginationInfo) -> "PaginationInfo":
        return cls(has_next=pagination.has_next, next_page=pagination.next_page, total_size=pagination.size)


class MultipageList(pydantic.BaseModel, typing.Generic[T]):
    model_config = pydantic.ConfigDict(frozen=True, arbitrary_types_allowed=True)

    items: typing.List[T] = pydantic.Field(description="The result items for this page.")
    pagination: PaginationInfo = pydantic.Field(
        description="Pagination state, including whether more results exist and how to fetch them.",
    )
