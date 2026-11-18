"""Framework-neutral registry of the existing game application operations."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class OperationError(Exception):
    """An application failure with an HTTP-compatible public status."""

    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


@dataclass
class FileAsset:
    """An application asset, resolved by each transport."""

    path: Path
    media_type: str


@dataclass
class Operation:
    method: str
    path: str
    handler: Callable
    response_model: Any = None


class OperationRegistry:
    """Register a fixed set of named HTTP-shaped application operations."""

    def __init__(self) -> None:
        self.operations: list[Operation] = []

    def _register(self, method: str, path: str, response_model: Any = None) -> Callable:
        def decorate(handler: Callable) -> Callable:
            self.operations.append(Operation(method, path, handler, response_model))
            return handler
        return decorate

    def get(self, path: str, response_model: Any = None) -> Callable:
        return self._register("GET", path, response_model)

    def post(self, path: str, response_model: Any = None) -> Callable:
        return self._register("POST", path, response_model)

    def delete(self, path: str, response_model: Any = None) -> Callable:
        return self._register("DELETE", path, response_model)
