"""Verify release builds publish generated charts with their attribution."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_FILES = (
    "paydirt.spec",
    "paydirt_dir.spec",
    "paydirt_onefile.spec",
    "__main__.spec",
)


def test_pyinstaller_specs_bundle_public_seasons_and_chart_attribution() -> None:
    """Every supported PyInstaller entry point includes the same public chart data."""
    for relative_path in SPEC_FILES:
        text = (ROOT / relative_path).read_text()
        assert "('seasons/1983-generated', 'seasons/1983')" in text, relative_path
        assert "('seasons/2024', 'seasons/2024')" in text, relative_path
        assert "('seasons/2026', 'seasons/2026')" in text, relative_path
        assert "CHART_ATTRIBUTION.md" in text, relative_path


def test_platform_packages_expose_chart_attribution() -> None:
    """Installed applications leave the chart source notice available to players."""
    package_files = (
        "packaging/macos/create_app.sh",
        "packaging/linux/create_appimage.sh",
        "packaging/windows/installer.nsi",
    )
    for relative_path in package_files:
        text = (ROOT / relative_path).read_text()
        assert "CHART_ATTRIBUTION.md" in text, relative_path


def test_public_generated_seasons_are_not_ignored() -> None:
    """Generated release data is tracked while original and intermediate charts stay private."""
    ignore_text = (ROOT / ".gitignore").read_text()
    assert "seasons/1983-generated/" not in ignore_text
    assert "seasons/2024/" not in ignore_text
    assert "seasons/1983/" in ignore_text
    assert "seasons/1983-pbp-joint-final/" in ignore_text


def test_chart_attribution_describes_generated_sources_and_license() -> None:
    """The distributed notice identifies both data sources and the chart license."""
    text = (ROOT / "CHART_ATTRIBUTION.md").read_text()
    assert "independent statistical reconstructions" in text
    assert "Pro Football Reference" in text
    assert "nflverse" in text
    assert "CC BY 4.0" in text
    assert "MIT License" in text
    assert "No original Paydirt team charts" in text

    in_app_notice = (ROOT / "docs/seasons.md").read_text()
    assert "archived Pro Football Reference" in in_app_notice
    assert "nflverse play-by-play is provided under CC BY 4.0" in in_app_notice


def test_bundled_backend_can_find_its_local_imports(tmp_path: Path) -> None:
    """The runtime-loaded routes need their local helpers outside the module archive."""
    import ast
    import shutil
    from importlib.machinery import PathFinder

    tree = ast.parse((ROOT / "paydirt.spec").read_text())
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "datas"
                              for target in node.targets))
    for source, destination in ast.literal_eval(assignment.value):
        if not source.startswith("paydirt-web/backend/") or not source.endswith(".py"):
            continue
        staged = tmp_path / destination / Path(source).name
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, staged)

    backend = ROOT / "paydirt-web/backend"
    routes = ast.parse((backend / "routes.py").read_text())
    local_modules = {node.module for node in ast.walk(routes)
                     if isinstance(node, ast.ImportFrom) and node.module
                     and (backend / f"{node.module}.py").is_file()}
    assert "chart_viewer" in local_modules, "The chart API must exercise its actual helper import"
    for module in local_modules:
        spec = PathFinder.find_spec(module, [str(tmp_path / "paydirt-web/backend")])
        assert spec is not None, f"Bundled routes cannot import local helper {module}"
        assert Path(spec.origin).read_bytes() == (backend / f"{module}.py").read_bytes()


def test_runtime_loaded_backend_core_dependencies_are_collected() -> None:
    """Dynamic backend files need every core module in the executable's import graph."""
    import ast

    tree = ast.parse((ROOT / "paydirt.spec").read_text())
    data_assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                           and any(isinstance(target, ast.Name) and target.id == "datas"
                                   for target in node.targets))
    backend_files = [ROOT / source for source, _ in ast.literal_eval(data_assignment.value)
                     if source.startswith("paydirt-web/backend/") and source.endswith(".py")]
    analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
    hidden_imports = next(keyword.value for keyword in analysis.keywords
                          if keyword.arg == "hiddenimports")
    collected = {node.value for node in ast.walk(hidden_imports)
                 if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    modules = {"paydirt." + path.stem: path for path in (ROOT / "paydirt").glob("*.py")}
    modules["paydirt"] = ROOT / "paydirt/__init__.py"

    def imports(path: Path) -> set[str]:
        names = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                parent = ("paydirt." if node.level else "") + (node.module or "")
                names.add(parent)
                names.update(parent + "." + alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
        return names & modules.keys()

    pending = {"paydirt"} | imports(ROOT / "paydirt_runner.py") | (collected & modules.keys())
    visited = set()
    while pending:
        module = pending.pop()
        if module not in visited:
            visited.add(module)
            collected.add(module)
            pending.update(imports(modules[module]) - visited)
    required = set().union(*(imports(path) for path in backend_files))
    assert required, "The bundled backend must exercise its actual engine imports"
    assert required <= collected, f"Uncollected dynamic backend dependencies: {sorted(required - collected)}"


def test_release_specs_include_new_season_without_replacing_existing_seasons() -> None:
    """Configuration-only check; never opens historical team data."""
    for relative_path in SPEC_FILES:
        text = (ROOT / relative_path).read_text()
        assert "('seasons/1977', 'seasons/1977')" in text, relative_path
        assert "('seasons/2026', 'seasons/2026')" in text, relative_path


def test_ci_and_release_public_chart_matrices_cover_new_season() -> None:
    """Both publication stages must validate the added season's public structure."""
    import yaml

    for relative_path in (".github/workflows/test.yml", ".github/workflows/release.yml"):
        workflow = yaml.safe_load((ROOT / relative_path).read_text())
        matrix = workflow["jobs"]["chart-quality"]["strategy"]["matrix"]["include"]
        assert {"directory": "1977", "season": 1977, "teams": 28} in matrix, relative_path
