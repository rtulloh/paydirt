"""Release orchestration must reuse only exact-commit successful CI."""
import io
import json
import runpy
import urllib.request
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


def workflow():
    return yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())


def test_release_dispatch_and_pinned_builds():
    data = workflow()
    trigger = data.get("on", data.get(True))
    assert trigger["workflow_dispatch"]["inputs"]["release_tag"]["required"] is True
    jobs = data["jobs"]
    assert "test" not in jobs
    assert jobs["verify-ci"]["permissions"] == {"actions": "read", "contents": "read"}
    for name in ("chart-quality", "build"):
        assert "verify-ci" in jobs[name]["needs"]
        checkout = next(s for s in jobs[name]["steps"] if s.get("uses", "").startswith("actions/checkout@"))
        assert checkout["with"]["ref"] == "${{ needs.verify-ci.outputs.sha }}"
    build = jobs["build"]
    assert build["env"]["RELEASE_TAG"] == "${{ needs.verify-ci.outputs.tag }}"
    for platform in ("macos/create_app.sh", "linux/create_appimage.sh"):
        command = next(s["run"] for s in build["steps"] if platform in s.get("run", ""))
        assert 'env GITHUB_REF_NAME="$RELEASE_TAG"' in command
    release = jobs["release"]
    assert "verify-ci" in release["needs"]
    publish = next(s for s in release["steps"] if s.get("uses", "").startswith("softprops/"))
    assert publish["with"]["tag_name"] == "${{ needs.verify-ci.outputs.tag }}"
    assert len(publish["with"]["files"].splitlines()) == 5


@pytest.mark.parametrize("head,status,conclusion,path,accepted", [
    (SHA, "completed", "success", ".github/workflows/test.yml", True),
    ("b" * 40, "completed", "success", ".github/workflows/test.yml", False),
    (SHA, "in_progress", "success", ".github/workflows/test.yml", False),
    (SHA, "completed", "failure", ".github/workflows/test.yml", False),
    (SHA, "completed", "success", ".github/workflows/other.yml", False),
])
@pytest.mark.parametrize("annotated", [False, True])
def test_gate_requires_exact_success(monkeypatch, tmp_path, head, status, conclusion, path, accepted, annotated):
    step = workflow()["jobs"]["verify-ci"]["steps"][0]
    code = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    script = tmp_path / "release_gate.py"
    script.write_text(code)
    output = tmp_path / "output"
    for key, value in {"GH_REPO": "owner/repo", "GH_TOKEN": "synthetic", "GH_API_URL": "https://api.example", "RELEASE_TAG": "v1.10.1", "GITHUB_OUTPUT": str(output)}.items():
        monkeypatch.setenv(key, value)
    urls = []
    def request(req, timeout):
        assert timeout == 30
        url = req.full_url
        urls.append(url)
        if "/git/ref/tags/" in url:
            value = {"object": {"type": "tag" if annotated else "commit", "sha": "c" * 40 if annotated else SHA}}
        elif "/git/tags/" in url:
            value = {"object": {"type": "commit", "sha": SHA}}
        else:
            assert "/actions/workflows/test.yml/runs?head_sha=" + SHA in url
            value = {"workflow_runs": [{"head_sha": head, "status": status, "conclusion": conclusion, "path": path, "html_url": "https://example/run"}]}
        return io.BytesIO(json.dumps(value).encode())
    monkeypatch.setattr(urllib.request, "urlopen", request)
    if accepted:
        runpy.run_path(str(script), run_name="__main__")
        assert output.read_text() == f"sha={SHA}\ntag=v1.10.1\n"
    else:
        with pytest.raises(SystemExit):
            runpy.run_path(str(script), run_name="__main__")
        assert not output.exists()


def test_publication_uses_existing_tag_without_workflow_restricted_target():
    release = workflow()["jobs"]["release"]
    publish = next(s for s in release["steps"] if s.get("uses", "").startswith("softprops/"))
    assert "target_commitish" not in publish["with"]
    guard = next(s for s in release["steps"] if s["name"] == "Recheck existing immutable tag before publication")
    assert guard["env"]["EXPECTED_SHA"] == "${{ needs.verify-ci.outputs.sha }}"
    assert guard["env"]["RELEASE_TAG"] == "${{ needs.verify-ci.outputs.tag }}"
    assert release["steps"].index(guard) < release["steps"].index(publish)


@pytest.mark.parametrize("tag_sha", [SHA, "b" * 40])
@pytest.mark.parametrize("annotated", [False, True])
def test_publication_rejects_a_moved_tag(monkeypatch, tmp_path, tag_sha, annotated):
    steps = workflow()["jobs"]["release"]["steps"]
    guard = next((s for s in steps if s["name"] == "Recheck existing immutable tag before publication"), None)
    assert guard is not None, "Publication must recheck the existing tested tag"
    code = guard["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    script = tmp_path / "publish_guard.py"
    script.write_text(code)
    for key, value in {"GH_REPO": "owner/repo", "GH_TOKEN": "synthetic", "GH_API_URL": "https://api.example", "RELEASE_TAG": "v1.10.2", "EXPECTED_SHA": SHA}.items():
        monkeypatch.setenv(key, value)
    def request(req, timeout):
        assert timeout == 30
        obj = {"type": "commit", "sha": tag_sha}
        if annotated and "/git/ref/tags/" in req.full_url:
            obj = {"type": "tag", "sha": "c" * 40}
        return io.BytesIO(json.dumps({"object": obj}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", request)
    if tag_sha == SHA:
        runpy.run_path(str(script), run_name="__main__")
    else:
        with pytest.raises(SystemExit, match="Existing tag no longer matches"):
            runpy.run_path(str(script), run_name="__main__")


@pytest.mark.parametrize("event,run_event,head,accepted", [
    ("workflow_dispatch", "workflow_dispatch", SHA, True),
    ("push", "workflow_dispatch", SHA, False),
    ("workflow_dispatch", "push", SHA, False),
    ("workflow_dispatch", "workflow_dispatch", "b" * 40, False),
])
def test_manual_hotfix_qualification(monkeypatch, tmp_path, event, run_event, head, accepted):
    data = workflow()
    trigger = data.get("on", data.get(True))
    option = trigger["workflow_dispatch"]["inputs"]["qualification_workflow"]
    assert option["default"] == "test.yml"
    assert option["options"] == ["test.yml", "hotfix.yml"]
    code = data["jobs"]["verify-ci"]["steps"][0]["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    script = tmp_path / "gate.py"
    script.write_text(code)
    output = tmp_path / "output"
    for key, value in {"GH_REPO": "owner/repo", "GH_TOKEN": "synthetic", "GH_API_URL": "https://api.example", "RELEASE_TAG": "v1.10.3", "GITHUB_OUTPUT": str(output), "QUALIFICATION_WORKFLOW": "hotfix.yml", "RELEASE_EVENT_NAME": event}.items():
        monkeypatch.setenv(key, value)
    def request(req, timeout):
        if "/git/ref/tags/" in req.full_url:
            value = {"object": {"type": "commit", "sha": SHA}}
        else:
            assert "/actions/workflows/hotfix.yml/runs?head_sha=" + SHA in req.full_url
            value = {"workflow_runs": [{"head_sha": head, "status": "completed", "conclusion": "success", "path": ".github/workflows/hotfix.yml", "event": run_event, "html_url": "https://example/run"}]}
        return io.BytesIO(json.dumps(value).encode())
    monkeypatch.setattr(urllib.request, "urlopen", request)
    if accepted:
        runpy.run_path(str(script), run_name="__main__")
        assert output.read_text() == f"sha={SHA}\ntag=v1.10.3\n"
    else:
        with pytest.raises(SystemExit):
            runpy.run_path(str(script), run_name="__main__")
        assert not output.exists()


def test_release_build_installs_the_tested_backend_runtime_requirements():
    """Frozen applications must use the same runtime versions as backend CI."""
    import shlex

    steps = workflow()["jobs"]["build"]["steps"]
    install = next(step for step in steps if step.get("name") == "Install dependencies")
    commands = [shlex.split(line) for line in install["run"].splitlines() if line.strip()]
    requirements = "paydirt-web/backend/requirements.txt"
    assert any("-r" in words and words[words.index("-r") + 1] == requirements
               for words in commands), "Native packages must install the backend runtime requirements"
    runtime = {line.split("==")[0].split("[")[0].lower()
               for line in (ROOT / requirements).read_text().splitlines()
               if line.strip() and not line.startswith("#")}
    for words in commands:
        if "install" in words:
            assert not (runtime & {word.lower() for word in words}), "Unbounded runtime overrides the tested pins"
    assert ["python", "-m", "pip", "check"] in commands
    assert ["python", "-m", "pip", "freeze", ">", "build-requirements.txt"] in commands
    evidence = next(step for step in steps if step.get("name") == "Preserve resolved build dependencies")
    assert evidence["with"]["path"] == "build-requirements.txt"
    assert evidence["with"]["if-no-files-found"] == "error"
    build = next(step for step in steps if step.get("name") == "Build executable")
    assert steps.index(install) < steps.index(build)


def test_backend_runtime_manifest_keeps_compatible_fastapi_and_models_pinned():
    requirements = (ROOT / "paydirt-web/backend/requirements.txt").read_text().splitlines()
    assert "fastapi==0.109.0" in requirements
    assert "pydantic==2.5.0" in requirements
    assert "uvicorn[standard]==0.27.0" in requirements


def test_windows_installer_failures_stop_the_release_build():
    steps = workflow()["jobs"]["build"]["steps"]
    for name in ("Install NSIS", "Create Windows installer"):
        step = next(step for step in steps if step.get("name") == name)
        assert step.get("continue-on-error", False) is False, f"{name} must fail closed"


@pytest.mark.parametrize("defect", [None, "linux", "portable", "installer", "arm64", "intel", "empty", "symlink", "extra-dmg"])
def test_publication_requires_every_nonempty_exact_version_package(monkeypatch, tmp_path, defect):
    steps = workflow()["jobs"]["release"]["steps"]
    guard = next((step for step in steps if step.get("name") == "Verify all five mandatory release packages"), None)
    assert guard is not None, "Publication needs an explicit five-package completeness gate"
    publish = next(step for step in steps if step.get("uses", "").startswith("softprops/"))
    download = next(step for step in steps if step.get("uses", "").startswith("actions/download-artifact@"))
    assert steps.index(download) < steps.index(guard) < steps.index(publish)
    assert guard["env"]["RELEASE_TAG"] == "${{ needs.verify-ci.outputs.tag }}"
    files = {
        "linux": "paydirt-linux/Paydirt-x86_64.AppImage",
        "portable": "paydirt-windows/paydirt.exe",
        "installer": "paydirt-windows/PaydirtSetup.exe",
        "arm64": "paydirt-macos-arm64/Paydirt-9.9.9-arm64.dmg",
        "intel": "paydirt-macos-intel/Paydirt-9.9.9-x86_64.dmg",
    }
    for relative in files.values():
        path = tmp_path / "artifacts" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic package; never executed")
    if defect in files:
        (tmp_path / "artifacts" / files[defect]).unlink()
    elif defect == "empty":
        (tmp_path / "artifacts" / files["installer"]).write_bytes(b"")
    elif defect == "symlink":
        path = tmp_path / "artifacts" / files["installer"]
        path.unlink()
        path.symlink_to(tmp_path / "artifacts" / files["portable"])
    elif defect == "extra-dmg":
        (tmp_path / "artifacts/paydirt-macos-arm64/Paydirt-OLD-arm64.dmg").write_bytes(b"stale")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RELEASE_TAG", "v9.9.9")
    code = guard["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    script = tmp_path / "package_gate.py"
    script.write_text(code)
    if defect is None:
        runpy.run_path(str(script), run_name="__main__")
    else:
        with pytest.raises(SystemExit, match="release package"):
            runpy.run_path(str(script), run_name="__main__")


def test_release_upload_rejects_any_unmatched_mandatory_file():
    publish = next(step for step in workflow()["jobs"]["release"]["steps"]
                   if step.get("uses", "").startswith("softprops/"))
    assert publish["with"].get("fail_on_unmatched_files") is True


def test_release_body_prioritizes_browser_play_without_a_security_override():
    publish = next(step for step in workflow()["jobs"]["release"]["steps"]
                   if step.get("uses", "").startswith("softprops/"))
    body = publish["with"]["body"]
    assert body.index("https://rtulloh.github.io/paydirt/") < body.index("Optional desktop downloads")
    assert "browser profile" in body and "Export" in body
    assert "not notarized" in body and "first launch" in body
    assert "xattr" not in body and "spctl --master-disable" not in body
