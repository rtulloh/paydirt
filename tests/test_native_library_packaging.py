"""Runtime-loaded native storage stays available without enabling it in Wasm."""
import ast
from pathlib import Path

from scripts.build_browser_spike import PUBLIC_FILES

ROOT = Path(__file__).resolve().parents[1]


def test_native_release_contains_storage_modules_and_sqlite_runtime() -> None:
    """Source-loaded backend modules and their lazy sqlite dependency are packaged."""
    tree = ast.parse((ROOT / "paydirt.spec").read_text())
    data = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "datas" for target in node.targets))
    entries = ast.literal_eval(data)
    for name in ("native_library", "native_library_operations"):
        assert (f"paydirt-web/backend/{name}.py", "paydirt-web/backend") in entries
    analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
    hidden = next(keyword.value for keyword in analysis.keywords if keyword.arg == "hiddenimports")
    strings = {node.value for node in ast.walk(hidden) if isinstance(node, ast.Constant)}
    assert {"sqlite3", "_sqlite3"} <= strings


def test_browser_contains_native_registry_without_sqlite_import_side_effect() -> None:
    """The shared routes can import, while disabled browser mode needs no sqlite."""
    assert "paydirt-web/backend/native_library_operations.py" in PUBLIC_FILES
    assert "paydirt-web/backend/native_library.py" not in PUBLIC_FILES
    tree = ast.parse((ROOT / "paydirt-web/backend/native_library_operations.py").read_text())
    top_imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    names = {alias.name for node in top_imports if isinstance(node, ast.Import) for alias in node.names}
    modules = {node.module for node in top_imports if isinstance(node, ast.ImportFrom)}
    assert "sqlite3" not in names
    assert "native_library" not in modules
