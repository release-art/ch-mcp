"""Convert session request params to cache filename used in tests."""

import hashlib
import json
import logging
import pathlib
import typing
from typing import Any

logger = logging.getLogger(__name__)
G_CUR_TEST_PREFIX: typing.Optional[pathlib.PurePath] = None


def make(method: str, args: tuple[Any, ...]) -> pathlib.PurePath:  # noqa: C901
    """Generate a cache filename based on the request parameters.

    Creates human-readable cache filenames by:
    - Using the last URL path segment as a directory name
    - Creating descriptive filenames based on request parameters
    - Adding a hash suffix for uniqueness

    Parameters
    ----------
    method : str

    headers : dict
        The request headers.
    **kwargs : Any
        Additional request parameters.

    Returns
    -------
    pathlib.PurePath
        Path to the cache file with directory structure.
    """

    # Build human-readable filename components
    filename_parts = [method.lower()]

    # Create base filename
    if filename_parts:
        base_filename = "_".join(filename_parts)
    else:
        base_filename = "request"

    cache_key = json.dumps({"args": args}, sort_keys=True)
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]  # Use first 8 chars

    # Combine into final filename
    final_filename = f"{base_filename}_{cache_hash}.json"

    assert G_CUR_TEST_PREFIX is not None, "G_CUR_TEST_PREFIX must be set before calling make()"
    out = G_CUR_TEST_PREFIX / final_filename
    logger.info(f"Generated cache filename: {out}")
    return out
