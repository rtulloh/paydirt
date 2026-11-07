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
