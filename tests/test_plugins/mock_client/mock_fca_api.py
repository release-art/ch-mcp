from __future__ import annotations

import enum
import json
import pathlib
import typing

import fca_api
import httpx
import pydantic

from . import cache_filename, mock_data


@enum.unique
class CacheMode(enum.StrEnum):
    READ = "readonly"
    WRITE = "writeonly"
    FETCH_MISSING = "fetch_missing"


class MockFcaApi:
    """Mock FCA API client that uses CachingSession for testing."""

    cache_dir: pathlib.Path
    api_implementation: typing.Type[httpx.AsyncClient] | None

    def __init__(self, api_implementation: typing.Type[httpx.AsyncClient] = None):
        self.cache_dir = pathlib.Path(__file__).parent.parent.parent / "mock_fca_api_cache"
        self.api_implementation = api_implementation

    async def __aenter__(self) -> MockFcaApi:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def _get_cache_filename(self, method_name: str, args: tuple[typing.Any]) -> pathlib.Path:
        """Generate a cache filename based on the request parameters.

        Parameters
        ----------
        url : str
            The request URL.
        **kwargs : Any
            Additional request parameters.

        Returns
        -------
        pathlib.Path
            Path to the cache file.
        """
        # Create a unique identifier from URL and request parameters
        # This must match the logic in CachingFinancialServicesRegisterApiSession
        return self.cache_dir / cache_filename.make(method_name, args=args)

    def __getattr__(self, method_name):
        async def mock_api_method(*args, **kwargs):
            cache_filename = self._get_cache_filename(method_name, args)
            if cache_filename.exists():
                with cache_filename.open("r") as f:
                    cached_data = json.load(f)
                if cached_data is None:
                    out = None
                else:
                    assert isinstance(cached_data, dict), f"Expected cached data to be a dict, got {type(cached_data)}"
                    if cached_data.get("type") == "PydanticModel":
                        out = mock_data.PydanticModel.from_dict(cached_data)
                    elif cached_data.get("type") == "MultipageList":
                        out = mock_data.MockMultipageListReadOnly(cached_data)
                    else:
                        raise NotImplementedError(f"Unexpected cached data type: {cached_data.get('type')}")
                return out
            else:
                # No cached response, call the real API implementation if available
                if self.api_implementation:
                    out = await getattr(self.api_implementation, method_name)(*args, **kwargs)
                    if isinstance(out, pydantic.BaseModel):
                        cached_value = mock_data.PydanticModel.to_dict(out)
                    elif isinstance(out, fca_api.types.pagination.MultipageList):
                        out = mock_data.MockMultipageListSource(
                            cached_file=cache_filename,
                            src=out,
                        )
                        cached_value = out.get_state()
                    elif out is None:
                        cached_value = out
                    else:
                        raise NotImplementedError(f"Unexpected return type from API implementation: {type(out)}")
                    cache_filename.parent.mkdir(parents=True, exist_ok=True)
                    with cache_filename.open("w") as f:
                        json.dump(cached_value, f, indent=2, sort_keys=True)
                    return out
                raise FileNotFoundError(
                    f"No cached response found for {method_name} with args {args} and kwargs {kwargs}"
                )

        return mock_api_method
