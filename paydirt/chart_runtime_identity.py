"""Bind audit evidence to loaded definitions, their origins and policy constants.

This detects stale imports and ordinary runtime replacement. It is a consistency
check inside a trusted Python process, not hostile-process attestation.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import sys
from enum import Enum
from pathlib import Path
from types import CodeType, FunctionType
from typing import Any

# These two flags are mutable display preferences set by ordinary CLI sessions,
# not audit/coaching policy constants. Their setters remain definition-checked.
_DISPLAY_STATE = {"interactive_game": {"COMPACT_MODE", "AI_HELPER_ENABLED"}}


def _code_hash(code: CodeType) -> str:
    # Marshal preserves incidental string-interning/reference flags: equal code
    # loaded from pyc and compiled from source can therefore serialize differently.
    def constant(value: Any) -> Any:
        if isinstance(value, CodeType):
            return ("code", _code_hash(value))
        if isinstance(value, (tuple, frozenset)):
            items = [constant(item) for item in value]
            return (type(value).__name__, tuple(sorted(items, key=repr) if isinstance(value, frozenset) else items))
        return (type(value).__name__, repr(value))

    fields = (code.co_argcount, code.co_posonlyargcount, code.co_kwonlyargcount,
              code.co_nlocals, code.co_stacksize, code.co_flags, code.co_code.hex(),
              tuple(constant(value) for value in code.co_consts), code.co_names,
              code.co_varnames, code.co_filename, code.co_name, getattr(code, "co_qualname", code.co_name),
              code.co_firstlineno, code.co_linetable.hex(), getattr(code, "co_exceptiontable", b"").hex(),
              code.co_freevars, code.co_cellvars)
    return hashlib.sha256(repr(fields).encode()).hexdigest()


def _compiled_codes(code: CodeType, prefix: str = "") -> dict[str, set[str]]:
    codes: dict[str, set[str]] = {}
    for value in code.co_consts:
        if isinstance(value, CodeType):
            qualified = getattr(value, "co_qualname", prefix + value.co_name)
            codes.setdefault(qualified, set()).add(_code_hash(value))
            for name, hashes in _compiled_codes(value, qualified + ".").items():
                codes.setdefault(name, set()).update(hashes)
    return codes


def _source_modules(root: Path) -> dict[str, tuple[Path, ast.Module]]:
    """Follow the actual audit/core relative imports, including lazy imports."""
    pending, sources = ["chart_engine_audit"], {}
    while pending:
        name = pending.pop()
        path = root / f"{name}.py"
        if name in sources or not path.is_file():
            continue
        tree = ast.parse(path.read_bytes(), filename=str(path))
        sources[name] = (path, tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module and "." not in node.module:
                    pending.append(node.module)
                elif node.module is None:
                    pending.extend(alias.name for alias in node.names)
    return sources


def _literal(node: ast.AST, values: dict[str, Any]) -> Any:
    """Resolve source literals/references without executing source expressions."""
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.Subscript):
        return _literal(node.value, values)[_literal(node.slice, values)]
    if isinstance(node, ast.Dict):
        return {_literal(key, values): _literal(value, values)
                for key, value in zip(node.keys, node.values)}
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        items = [_literal(value, values) for value in node.elts]
        return tuple(items) if isinstance(node, ast.Tuple) else set(items) if isinstance(node, ast.Set) else items
    return ast.literal_eval(node)


def _canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted(((_canonical(key), _canonical(item)) for key, item in value.items()), key=repr))
    if isinstance(value, (tuple, list, set)):
        items = [_canonical(item) for item in value]
        return tuple(sorted(items, key=repr)) if isinstance(value, set) else tuple(items)
    return value


def loaded_runtime_identity() -> dict[str, Any]:
    """Reject loaded objects that differ from freshly compiled package sources."""
    root = Path(__file__).resolve().parent
    sources = _source_modules(root)
    definitions, constants = [], []
    errors: list[str] = []
    for name, (path, tree) in sorted(sources.items()):
        module = importlib.import_module(f"{__package__}.{name}")
        if Path(module.__file__).resolve() != path:
            errors.append(f"{name}: module origin differs")
            continue
        compiled = _compiled_codes(compile(path.read_bytes(), str(path), "exec", dont_inherit=True))
        def inspect_body(
            owner: Any, nodes: list[ast.stmt], prefix: str = "",
            name: str = name, compiled: dict[str, set[str]] = compiled,
            inherited_values: dict[str, Any] | None = None,
        ) -> None:
            literal_values = dict(inherited_values or {})
            for node in nodes:
                label = prefix + getattr(node, "name", "")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    member = vars(owner).get(node.name)
                    functions = ([member.__func__] if isinstance(member, (classmethod, staticmethod)) else
                                 [fn for fn in (member.fget, member.fset, member.fdel) if fn is not None]
                                 if isinstance(member, property) else [member])
                    defaults = tuple(_literal(value, literal_values) for value in node.args.defaults) or None
                    keyword_defaults = {
                        argument.arg: _literal(value, literal_values)
                        for argument, value in zip(node.args.kwonlyargs, node.args.kw_defaults)
                        if value is not None
                    } or None
                    actual = []
                    for function in functions:
                        if not isinstance(function, FunctionType):
                            errors.append(f"{name}.{label}: loaded function replaced")
                            continue
                        digest = _code_hash(function.__code__)
                        if digest not in compiled.get(label, set()):
                            errors.append(f"{name}.{label}: loaded code differs from source")
                        if (_canonical(function.__defaults__) != _canonical(defaults)
                                or _canonical(function.__kwdefaults__) != _canonical(keyword_defaults)):
                            errors.append(f"{name}.{label}: loaded defaults differ from source")
                        # Class methods using super() legitimately capture their
                        # defining class. Other module/class declarations have
                        # no enclosing function scope in this audited package.
                        cells = function.__closure__ or ()
                        expected_cells = ((owner,) if isinstance(owner, type)
                                          and function.__code__.co_freevars == ("__class__",) else ())
                        try:
                            valid_cells = (len(cells) == len(expected_cells)
                                           and all(cell.cell_contents is expected
                                                   for cell, expected in zip(cells, expected_cells)))
                        except ValueError:  # An emptied closure cell is invalid.
                            valid_cells = False
                        if not valid_cells:
                            errors.append(f"{name}.{label}: loaded closure differs from defining class")
                        actual.append(digest)
                    definitions.append((name, label, sorted(set(actual)),
                                        _canonical(defaults), _canonical(keyword_defaults)))
                elif isinstance(node, ast.ClassDef):
                    member = vars(owner).get(node.name)
                    if not isinstance(member, type):
                        errors.append(f"{name}.{label}: loaded class replaced")
                    else:
                        inspect_body(member, node.body, label + ".", inherited_values=literal_values)
                elif isinstance(node, ast.Assign):
                    try:
                        expected = _literal(node.value, literal_values)
                    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
                        continue
                    for target in node.targets:
                        if not isinstance(target, ast.Name):
                            continue
                        literal_values[target.id] = expected
                        if (target.id.lstrip("_").isupper() or target.id == "normal_weights") and not (
                            isinstance(owner, type) and issubclass(owner, Enum)
                        ) and not (not prefix and target.id in _DISPLAY_STATE.get(name, set())):
                            if _canonical(vars(owner).get(target.id)) != _canonical(expected):
                                errors.append(f"{name}.{prefix}{target.id}: loaded constant differs")
                            constants.append((name, prefix + target.id, _canonical(expected)))
                elif isinstance(node, ast.ImportFrom) and not prefix and node.level == 1:
                    origin = importlib.import_module(f"{__package__}.{node.module}") if node.module else None
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        expected = (getattr(origin, alias.name) if origin else
                                    importlib.import_module(f"{__package__}.{alias.name}"))
                        if vars(owner).get(alias.asname or alias.name) is not expected:
                            errors.append(f"{name}.{alias.asname or alias.name}: loaded import differs")

        inspect_body(module, tree.body)
    if errors:
        raise RuntimeError("Invalid loaded runtime: " + "; ".join(errors[:12]))
    return {
        "scheme": "compiled-loaded-definitions-v1", "python": sys.implementation.cache_tag,
        "optimization": sys.flags.optimize,
        "module_files": [f"{name}.py" for name in sorted(sources)],
        "definitions_sha256": hashlib.sha256(repr(definitions).encode()).hexdigest(),
        "constants_sha256": hashlib.sha256(repr(constants).encode()).hexdigest(),
    }
