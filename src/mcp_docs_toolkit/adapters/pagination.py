"""Small pagination helper for mock adapters."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def page_items(items: list[T], page_cursor: str | None = None, page_size: int = 100) -> tuple[list[T], str | None]:
    try:
        start = max(int(page_cursor or "0"), 0)
    except ValueError:
        start = 0
    size = max(page_size, 0)
    end = start + size
    page = items[start:end]
    next_cursor = str(end) if end < len(items) else None
    return page, next_cursor


def add_next_cursor(data: dict[str, object], next_cursor: str | None) -> dict[str, object]:
    if next_cursor is not None:
        data["nextCursor"] = next_cursor
    return data
