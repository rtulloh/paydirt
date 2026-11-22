"""Partition a pytest collection across independent CI runners."""

from collections.abc import Callable, Sequence
from typing import TypeVar

import pytest

T = TypeVar('T')


def shard_items(items: Sequence[T], index: int, count: int, *, key: Callable[[T], str]) -> list[T]:
    """Spread adjacent test cases across runners and retain execution order."""
    selected = set(sorted(map(key, items))[index::count])
    return [item for item in items if key(item) in selected]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption('--shard-index', type=int, default=0)
    parser.addoption('--shard-count', type=int, default=1)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    index = config.getoption('--shard-index')
    count = config.getoption('--shard-count')
    if not 0 <= index < count:
        raise pytest.UsageError('Expected 0 <= --shard-index < --shard-count')
    selected = shard_items(items, index, count, key=lambda item: item.nodeid)
    selected_items = set(selected)
    config.hook.pytest_deselected(items=[item for item in items if item not in selected_items])
    items[:] = selected
