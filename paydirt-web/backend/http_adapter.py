"""Native FastAPI transport for the shared game operations."""
from collections.abc import Callable
from functools import wraps
from inspect import signature
from typing import Any, get_type_hints

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from operations import FileAsset, OperationError, OperationRegistry


def _endpoint(handler: Callable) -> Callable:
    @wraps(handler)
    async def invoke(*args: Any, **kwargs: Any) -> Any:
        try:
            result = await handler(*args, **kwargs)
        except OperationError as error:
            raise HTTPException(error.status_code, error.detail) from error
        if isinstance(result, FileAsset):
            return FileResponse(result.path, media_type=result.media_type)
        return result
    hints = get_type_hints(handler)
    original = signature(handler)
    invoke.__signature__ = original.replace(
        parameters=[parameter.replace(annotation=hints.get(name, parameter.annotation))
                    for name, parameter in original.parameters.items()],
        return_annotation=hints.get("return", original.return_annotation),
    )
    return invoke


def build_router(registry: OperationRegistry) -> APIRouter:
    """Adapt the supplied registry without binding a different module's session."""
    router = APIRouter()
    for operation in registry.operations:
        router.add_api_route(
            operation.path, _endpoint(operation.handler),
            methods=[operation.method], response_model=operation.response_model,
        )
    return router
