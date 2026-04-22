import pathlib

import ch_api.types.pagination.types as _ch_pagination
import pydantic
from ch_api.types.pagination.types import PaginationInfo


class PydanticModel:
    @staticmethod
    def to_dict(obj: pydantic.BaseModel) -> dict:
        return {
            "type": "PydanticModel",
            "module": obj.__module__,
            "class": obj.__class__.__name__,
            "data": obj.model_dump(mode="json", by_alias=True),
        }

    @staticmethod
    def from_dict(d: dict) -> pydantic.BaseModel:
        assert d["type"] == "PydanticModel"
        module = __import__(d["module"], fromlist=[d["class"]])
        cls = getattr(module, d["class"])
        return cls.model_validate(d["data"])


class MockMultipageListReadOnly:
    def __init__(self, cached_data: dict):
        if "data" in cached_data:
            self._data = [PydanticModel.from_dict(el) for el in cached_data["data"]]
            p = cached_data["pagination"]
            self._pagination = PaginationInfo(
                has_next=p["has_next"],
                next_page=p.get("next_page"),
                size=p.get("size"),
            )
        else:
            calls = cached_data.get("calls", [])
            items_raw = calls[0]["out"] if calls and calls[0]["call"] == "local_items" else []
            self._data = [PydanticModel.from_dict(el) for el in items_raw]
            self._pagination = PaginationInfo(has_next=False, next_page=None, size=None)

    @property
    def data(self):
        return self._data

    @property
    def pagination(self) -> PaginationInfo:
        return self._pagination


class MockMultipageListSource:
    def __init__(self, cached_file: pathlib.Path, src: _ch_pagination.MultipageList):
        self.cached_file = cached_file
        self._data = src.data
        self._pagination = src.pagination

    @property
    def data(self):
        return self._data

    @property
    def pagination(self) -> PaginationInfo:
        return self._pagination

    def get_state(self) -> dict:
        return {
            "type": "MultipageList",
            "data": [PydanticModel.to_dict(el) for el in self._data],
            "pagination": {
                "has_next": self._pagination.has_next,
                "next_page": self._pagination.next_page,
                "size": self._pagination.size,
            },
        }
