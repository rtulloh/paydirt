"""JSON transport for the static-browser spike; imports no HTTP server."""
from __future__ import annotations

import asyncio
import base64
import inspect
import json
import logging
import re
from typing import Any, get_type_hints
from urllib.parse import parse_qs, unquote, urlsplit

from operations import FileAsset, OperationError
from pydantic import BaseModel, TypeAdapter, ValidationError
from routes import registry

_lock = asyncio.Lock()
_logger = logging.getLogger(__name__)


def _encode(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    return value


async def _dispatch(request: dict) -> dict:
    method = request.get("method")
    path = request.get("path")
    if not isinstance(method, str) or not isinstance(path, str):
        return {"status": 400, "body": {"detail": "method and path are required"}}
    target = urlsplit(path)
    if target.scheme or target.netloc or target.fragment:
        return {"status": 400, "body": {"detail": "Expected a local operation path"}}
    body = request.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError:
            return {"status": 400, "body": {"detail": "Invalid JSON body"}}
    query = parse_qs(target.query, keep_blank_values=True)
    for operation in registry.operations:
        pattern = re.sub(r"\{([a-zA-Z_][a-zA-Z_0-9]*)\}", r"(?P<\1>[^/]+)", operation.path)
        match = re.fullmatch(pattern, target.path)
        if operation.method != method.upper() or match is None:
            continue
        hints = get_type_hints(operation.handler)
        arguments = {}
        for name, parameter in inspect.signature(operation.handler).parameters.items():
            annotation = hints.get(name, str)
            if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                arguments[name] = annotation.model_validate(body)
            elif name in match.groupdict():
                arguments[name] = TypeAdapter(annotation).validate_python(unquote(match[name]))
            elif name in query:
                arguments[name] = TypeAdapter(annotation).validate_python(query[name][-1])
            elif parameter.default is inspect.Parameter.empty:
                return {"status": 422, "body": {"detail": f"Missing parameter: {name}"}}
        result = await operation.handler(**arguments)
        if isinstance(result, FileAsset):
            return {
                "status": 200, "body": base64.b64encode(result.path.read_bytes()).decode("ascii"),
                "media_type": result.media_type, "encoding": "base64",
            }
        if operation.response_model is not None:
            result = operation.response_model.model_validate(result)
        return {"status": 200, "body": _encode(result)}
    return {"status": 404, "body": {"detail": "Unknown operation"}}


async def dispatch_json(request_text: str) -> str:
    """Validate and serialize a single registered operation and its result."""
    try:
        request = json.loads(request_text)
        if not isinstance(request, dict):
            raise TypeError("Expected an object")
    except (ValueError, TypeError):
        return json.dumps({"status": 400, "body": {"detail": "Invalid request envelope"}})
    async with _lock:
        try:
            response = await _dispatch(request)
        except ValidationError as error:
            response = {"status": 422, "body": {"detail": json.loads(error.json(include_url=False))}}
        except OperationError as error:
            response = {"status": error.status_code, "body": {"detail": error.detail}}
        except Exception:
            _logger.exception("Browser operation failed")
            response = {"status": 500, "body": {"detail": "Operation failed"}}
    return json.dumps(response, allow_nan=False)
