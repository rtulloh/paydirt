"""Synthetic, offline migration regressions; never write to GitHub."""

import json
from pathlib import Path

import pytest

from scripts import migrate_github_issues as migration


def ticket(root: Path, name: str = "TEST-001", status: str = "open") -> Path:
    path = root / "issues" / "TEST" / (name + ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {name}\ntitle: 'Synthetic: quoted title'\nstatus: {status}\n"
        "priority: Low\ncreated-at: 2020-01-01\ntags:\n  - example\n---\n"
        "\n## Description\n\nKeep `code`, [link](../../notes.md) and history.\n"
        "\n## Comments\n\n--- 2020-01-02 03:04 ---\nOriginal comment.\n"
    )
    return path


class FakeGitHub:
    def __init__(self) -> None:
        self.issues: list[dict] = []
        self.labels: list[str] = []
        self.fail_close = False
        self.comments: dict[int, list[dict]] = {}
        self.fail_comment = False

    def list_issues(self) -> list[dict]:
        return self.issues

    def ensure_labels(self, names: list[str]) -> None:
        self.labels.extend(names)

    def create_issue(self, title: str, body: str, label: str) -> dict:
        item = {"number": len(self.issues) + 1, "title": title, "body": body,
                "state": "open", "html_url": "https://github.com/example/game/issues/1"}
        self.issues.append(item)
        return item

    def close_issue(self, number: int) -> None:
        if self.fail_close:
            raise RuntimeError("Synthetic interrupted close")
        self.issues[number - 1]["state"] = "closed"

    def list_comments(self, number: int) -> list[dict]:
        return self.comments.get(number, [])

    def create_comment(self, number: int, body: str) -> None:
        if self.fail_comment:
            raise RuntimeError("Synthetic interrupted history")
        self.comments.setdefault(number, []).append({"body": body})


def test_all_states_metadata_comments_and_relative_links_survive(tmp_path: Path) -> None:
    for n, state in enumerate(["open", "resolved", "closed"], 1):
        ticket(tmp_path, f"TEST-{n:03}", state)
    issues = migration.load_issues(tmp_path, Path("issues"))
    github = FakeGitHub()
    report = migration.migrate(issues, "example/game", client=github)
    assert len(report) == len(github.issues) == 3
    assert [i["state"] for i in github.issues] == ["open", "open", "closed"]
    assert github.labels == ["local-status:closed", "local-status:open", "local-status:resolved"]
    body = github.issues[1]["body"]
    assert "priority: Low" in body and "created-at: 2020-01-01" in body
    assert "Original comment." in body and "2020-01-02 03:04" in body
    assert "awaiting" in body.lower()
    assert "https://github.com/example/game/blob/main/issues/TEST/../../notes.md" not in body
    assert "https://github.com/example/game/blob/main/notes.md" in body
    assert github.issues[0]["title"] == "[TEST-001] Synthetic: quoted title"


def test_offline_plan_does_not_construct_github_client(tmp_path: Path, monkeypatch) -> None:
    ticket(tmp_path)
    monkeypatch.setattr(migration, "GhClient", lambda *a: pytest.fail("Network in preview"))
    report = tmp_path / "plan.json"
    assert migration.main(["--source-root", str(tmp_path), "--issues-dir", "issues",
                           "--repo", "example/game", "--report", str(report)]) == 0
    assert json.loads(report.read_text())["mode"] == "preview"


def test_rerun_retains_remote_edits_and_does_not_reopen_closed_issue(tmp_path: Path) -> None:
    ticket(tmp_path)
    issues = migration.load_issues(tmp_path, Path("issues"))
    github = FakeGitHub()
    migration.migrate(issues, "example/game", client=github)
    github.issues[0]["body"] += "\nCommunity update."
    github.issues[0]["state"] = "closed"
    result = migration.migrate(issues, "example/game", client=github)
    assert len(github.issues) == 1 and result[0]["action"] == "existing"
    assert github.issues[0]["body"].endswith("Community update.")
    assert github.issues[0]["state"] == "closed"


def test_resume_after_creation_before_close(tmp_path: Path) -> None:
    ticket(tmp_path, status="closed")
    issues = migration.load_issues(tmp_path, Path("issues"))
    github = FakeGitHub()
    github.fail_close = True
    with pytest.raises(RuntimeError, match="interrupted"):
        migration.migrate(issues, "example/game", client=github)
    github.fail_close = False
    migration.migrate(issues, "example/game", client=github)
    assert len(github.issues) == 1 and github.issues[0]["state"] == "closed"


def test_conflicts_fail_before_any_new_issue_or_label(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    ticket(tmp_path, "TEST-002")
    github = FakeGitHub()
    issues = migration.load_issues(tmp_path, Path("issues"))
    migration.migrate(issues[:1], "example/game", client=github)
    path.write_text(path.read_text().replace("Original comment.", "Changed history."))
    github.labels.clear()
    with pytest.raises(ValueError, match="changed"):
        migration.migrate(migration.load_issues(tmp_path, Path("issues")),
                          "example/game", client=github)
    assert len(github.issues) == 1 and not github.labels


@pytest.mark.parametrize("problem", ["unknown-status", "duplicate-id", "malformed", "status-list"])
def test_invalid_input_is_rejected(tmp_path: Path, problem: str) -> None:
    path = ticket(tmp_path)
    if problem == "unknown-status":
        path.write_text(path.read_text().replace("status: open", "status: surprise"))
    elif problem == "duplicate-id":
        path.with_name("copy.md").write_text(path.read_text())
    elif problem == "malformed":
        path.write_text("---\nid: [broken\n---\nbody")
    else:
        path.write_text(path.read_text().replace("status: open", "status: [open]"))
    with pytest.raises(ValueError):
        migration.load_issues(tmp_path, Path("issues"))


def test_legacy_unquoted_colon_title_is_supported(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    path.write_text(path.read_text().replace("'Synthetic: quoted title'", "Legacy: literal title"))
    assert migration.load_issues(tmp_path, Path("issues"))[0].title == "Legacy: literal title"


def test_folded_legacy_title_is_supported(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    path.write_text(path.read_text().replace("'Synthetic: quoted title'", "A title that\n  spans lines"))
    assert migration.load_issues(tmp_path, Path("issues"))[0].title == "A title that spans lines"


def test_large_history_is_complete_and_resumes_before_closing(tmp_path: Path) -> None:
    path = ticket(tmp_path, status="closed")
    path.write_text(path.read_text() + "\nLong history.\n" * 13000)
    issues = migration.load_issues(tmp_path, Path("issues"))
    github = FakeGitHub()
    github.fail_comment = True
    with pytest.raises(RuntimeError, match="interrupted history"):
        migration.migrate(issues, "example/game", client=github)
    assert github.issues[0]["state"] == "open"
    github.fail_comment = False
    migration.migrate(issues, "example/game", client=github)
    assert len(github.issues) == 1 and github.issues[0]["state"] == "closed"
    parts = migration.split_body(migration.render_body(issues[0], "example/game", "local-markdown", "main"))
    assert github.issues[0]["body"] == parts[0]
    assert len(github.comments[1]) == len(parts) - 1
    for part, comment in zip(parts[1:], github.comments[1]):
        assert comment["body"].endswith(part)
        assert len(comment["body"]) < 65536
    migration.migrate(issues, "example/game", client=github)
    assert len(github.comments[1]) == len(parts) - 1


def test_code_examples_are_not_rewritten(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    path.write_text(path.read_text() + "\n```md\n[x](../example.md)\n```\n`[x](../example.md)`\n")
    issue = migration.load_issues(tmp_path, Path("issues"))[0]
    body = migration.render_body(issue, "example/game", "local-markdown", "main")
    assert "```md\n[x](../example.md)\n```" in body
    assert "`[x](../example.md)`" in body


def test_duplicate_remote_marker_fails_before_writes(tmp_path: Path) -> None:
    ticket(tmp_path)
    issues = migration.load_issues(tmp_path, Path("issues"))
    github = FakeGitHub()
    migration.migrate(issues, "example/game", client=github)
    github.issues.append(dict(github.issues[0]))
    github.labels.clear()
    with pytest.raises(ValueError, match="Duplicate remote"):
        migration.migrate(issues, "example/game", client=github)
    assert not github.labels


def test_cli_requires_apply_report_and_leaves_source_untouched(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    before = path.read_bytes()
    with pytest.raises(SystemExit):
        migration.main(["--repo", "example/game", "--apply"])
    assert migration.main(["--source-root", str(tmp_path), "--issues-dir", "issues",
                           "--repo", "example/game", "--report", str(path)]) == 1
    assert path.read_bytes() == before


def test_symlink_sources_and_empty_directories_are_rejected(tmp_path: Path) -> None:
    folder = tmp_path / "issues"
    folder.mkdir()
    with pytest.raises(ValueError, match="No issue"):
        migration.load_issues(tmp_path, Path("issues"))
    (folder / "README.md").symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="Symlink"):
        migration.load_issues(tmp_path, Path("issues"))


def test_transport_missing_labels_comments_and_closure(monkeypatch) -> None:
    client = migration.GhClient("example/game")
    calls = []

    def api(path, method="GET", payload=None, **kwargs):
        calls.append((path, method, payload, kwargs))
        if path.startswith("labels?"):
            return [[{"name": "local-status:open"}]]
        if path.endswith("comments?per_page=100"):
            return [[{"body": "first"}], [{"body": "second"}]]
        return {}

    monkeypatch.setattr(client, "api", api)
    client.ensure_labels(["local-status:open", "local-status:closed"])
    assert [x[2]["name"] for x in calls if x[1] == "POST"] == ["local-status:closed"]
    assert client.list_comments(3) == [{"body": "first"}, {"body": "second"}]
    client.create_comment(3, "History")
    client.close_issue(3)
    assert calls[-2][0:3] == ("issues/3/comments", "POST", {"body": "History"})
    assert calls[-1][0:3] == ("issues/3", "PATCH", {"state": "closed", "state_reason": "completed"})


def test_full_cli_apply_checkpoints_id_url_mapping(tmp_path: Path, monkeypatch) -> None:
    ticket(tmp_path, status="closed")
    github = FakeGitHub()
    monkeypatch.setattr(migration, "GhClient", lambda *a: github)
    report = tmp_path / "mapping.json"
    assert migration.main(["--source-root", str(tmp_path), "--issues-dir", "issues",
                           "--repo", "example/game", "--apply", "--report", str(report)]) == 0
    saved = json.loads(report.read_text())
    assert saved["mode"] == "apply" and saved["issues"][0]["number"] == 1
    assert saved["issues"][0]["closure_pending"] is False


def test_cli_displays_github_permission_error(tmp_path: Path, monkeypatch, capsys) -> None:
    ticket(tmp_path)
    github = FakeGitHub()

    def rejected():
        raise migration.subprocess.CalledProcessError(
            1, ['gh', 'api'], stderr='Resource not accessible by personal access token (HTTP 403)')

    monkeypatch.setattr(github, 'list_issues', rejected)
    monkeypatch.setattr(migration, 'GhClient', lambda *a: github)
    assert migration.main(['--source-root', str(tmp_path), '--issues-dir', 'issues',
                           '--repo', 'example/game', '--apply',
                           '--report', str(tmp_path / 'mapping.json')]) == 1
    assert 'Resource not accessible' in capsys.readouterr().err
    assert not github.issues and not github.labels


def test_gh_uses_paginated_all_states_json_stdin_and_no_shell(monkeypatch) -> None:
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        class Result:
            stdout = '[[{"number": 1}], [{"number": 2, "pull_request": {}}]]'
        return Result()

    monkeypatch.setattr(migration.subprocess, "run", run)
    client = migration.GhClient("example/game")
    assert client.list_issues() == [{"number": 1}]
    args, kwargs = calls[-1]
    assert "--paginate" in args and "--slurp" in args
    assert any("state=all" in value for value in args)
    assert not kwargs.get("shell", False)
    client.create_issue("A `title`", "$(literal)\nnew line", "local-status:open")
    args, kwargs = calls[-1]
    assert args[-2:] == ["--input", "-"]
    assert json.loads(kwargs["input"])["body"] == "$(literal)\nnew line"
