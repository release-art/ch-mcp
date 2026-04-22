"""Mock session module for testing the Companies House API without network requests."""

import pathlib

import pytest

from . import cache_filename, mock_ch_api


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_setup(item):
    path_parts = []
    for el in reversed(item.listnames()):
        if el.strip():
            path_parts.insert(0, el)
        if el.lower().endswith(".py"):
            # Stop at the test file name
            break

    cache_filename.G_CUR_TEST_PREFIX = pathlib.PurePath(*path_parts)
    yield


@pytest.fixture
def caching_mock_api():
    return mock_ch_api.MockChApi
