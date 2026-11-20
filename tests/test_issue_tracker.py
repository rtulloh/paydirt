"""GitHub is canonical; local authoring is an ignored offline fallback only.

The former 480 per-ticket data checks and index-presence checks applied to files
now migrated to GitHub. Test the retained offline tools with synthetic fixtures,
and retain a public ID-to-GitHub mapping instead of copying historical tickets.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts import build_issue_index as index
from scripts import create_issue as author

ROOT = Path(__file__).resolve().parents[1]


def test_default_offline_store_does_not_recreate_removed_tracker() -> None:
    assert index.ISSUES == ROOT / '.ai-audits/offline-issues'
    assert index.INDEX == ROOT / '.ai-audits/offline-issue-tracker.md'


def test_index_can_initialize_empty_offline_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(index, 'ROOT', tmp_path)
    monkeypatch.setattr(index, 'ISSUES', tmp_path / '.ai-audits/offline-issues')
    monkeypatch.setattr(index, 'INDEX', tmp_path / '.ai-audits/offline-issue-tracker.md')
    assert index.main() == 0
    body = index.INDEX.read_text()
    assert '0 issues: 0 open, 0 resolved, 0 closed.' in body
    assert 'https://github.com/rtulloh/paydirt/issues' in body
    assert 'issues/README.md' not in body


@pytest.mark.parametrize('status', ['open', 'resolved', 'closed'])
def test_offline_render_preserves_status_and_history(tmp_path: Path, monkeypatch, status: str) -> None:
    monkeypatch.setattr(index, 'ROOT', tmp_path)
    monkeypatch.setattr(index, 'ISSUES', tmp_path / 'offline-issues')
    monkeypatch.setattr(index, 'INDEX', tmp_path / 'offline-index.md')
    path = author.create_issue('OFFLINE', 'Synthetic issue', 'Description', ['Verify'])
    text = path.read_text().replace('status: open', 'status: ' + status)
    text = re.sub(r'(?m)^created-at:.*$', 'created-at: 2020-01-01', text)
    if status != 'open':
        text = text.replace('resolved-at:\n', 'resolved-at: 2020-01-02\n')
    if status == 'closed':
        text = text.replace('closed-at:\n', 'closed-at: 2020-01-03\n')
    path.write_text(text + '\nPreserved synthetic history.\n')
    rendered = index.render_index(index.ISSUES)
    assert f'## {status.title()} (1)' in rendered or '## Resolved (awaiting play-test confirmation) (1)' in rendered
    assert '[OFFLINE-001](offline-issues/OFFLINE/OFFLINE-001.md)' in rendered
    assert 'Preserved synthetic history.' in path.read_text()


def test_migrated_sources_are_removed_and_mapping_is_complete() -> None:
    assert not (ROOT / 'docs/dev-notes/issues').exists()
    assert not (ROOT / 'docs/dev-notes/issue-tracker.md').exists()
    mapping = json.loads((ROOT / '.github/issue-migration.json').read_text())
    assert mapping['repo'] == 'rtulloh/paydirt'
    assert re.fullmatch(r'[0-9a-f]{40}', mapping['source_commit'])
    rows = mapping['issues']
    assert len(rows) == 240
    assert len({r['id'] for r in rows}) == len({r['number'] for r in rows}) == 240
    assert {state: sum(r['original_status'] == state for r in rows)
            for state in ['open', 'resolved', 'closed']} == {'open': 75, 'resolved': 76, 'closed': 89}
    for row in rows:
        assert row['url'] == f"https://github.com/rtulloh/paydirt/issues/{row['number']}"
        assert re.fullmatch(r'[0-9a-f]{64}', row['source_sha256'])
