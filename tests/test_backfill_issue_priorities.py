"""Synthetic controls for priority backfill planning."""
import pytest

from scripts.backfill_issue_priorities import choose_action, plan_priorities


def ticket(priority="High", number=1):
    return {"number": number, "body": (
        "<!-- local-issue-migration:v1:abc:TEST-001 -->\n"
        "<summary>Original metadata</summary>\n\n```yaml\n"
        f"id: TEST-001\npriority: {priority}\n```\n\n</details>\npriority: Low"
    )}


@pytest.mark.parametrize("priority", ["High", "Medium", "Low"])
def test_plan_preserves_original_priority(priority):
    assert plan_priorities([ticket(priority)])[0]["priority"] == priority


def test_unimported_and_pull_requests_are_ignored():
    assert plan_priorities([{"number": 1, "body": "priority: High"},
                            dict(ticket(), pull_request={})]) == []


def test_unknown_priority_stops_before_writes():
    with pytest.raises(ValueError, match="priority"):
        plan_priorities([ticket("Urgent")])


def test_existing_priority_is_preserved():
    assert choose_action([], 7, "High") == "set"
    assert choose_action([{"issue_field_id": 7, "single_select_option": {"name": "High"}}], 7, "High") == "unchanged"
    assert choose_action([{"issue_field_id": 7, "single_select_option": {"name": "Low"}}], 7, "High") == "conflict"
    assert choose_action([{"issue_field_id": 8, "value": "Other field"}], 7, "High") == "set"


def run_cli(monkeypatch, tmp_path, api, *extra):
    import sys

    from scripts import backfill_issue_priorities as module

    report = tmp_path / 'report.json'
    monkeypatch.setattr(sys, 'argv', ['backfill', '--repo', 'owner/repo',
                                    '--report', str(report), *extra])
    monkeypatch.setattr(module, 'api', api)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    module.main()
    import json
    return json.loads(report.read_text())


def test_preview_does_not_read_fields_or_write(monkeypatch, tmp_path):
    calls = []

    def api(path, payload=None, **kwargs):
        calls.append((path, payload))
        return [[ticket()]]

    report = run_cli(monkeypatch, tmp_path, api)
    assert report['plan'] == [{'number': 1, 'priority': 'High'}]
    assert len(calls) == 1 and calls[0][1] is None


def test_apply_creates_field_then_adds_only_priority_and_resumes(monkeypatch, tmp_path):
    fields = []
    values = {}
    writes = []

    def api(path, payload=None, **kwargs):
        if payload is not None:
            writes.append((path, payload))
        if path == 'user':
            return {'login': 'owner'}
        if path == 'user/issue-fields':
            if payload is not None:
                fields.append(dict(payload, id=7))
            return fields[-1] if payload is not None else fields
        if '/issue-field-values' in path:
            number = int(path.split('/')[4])
            if payload is not None:
                assert payload == {'issue_field_values': [{'field_id': 7, 'value': 'High'}]}
                values[number] = [{'issue_field_id': 7, 'single_select_option': {'name': 'High'}}]
                return values[number]
            return [values.get(number, [{'issue_field_id': 8, 'value': 'keep'}])]
        return [[ticket(number=n) for n in (1, 2)]]

    first = run_cli(monkeypatch, tmp_path, api, '--apply', '--limit', '1')
    assert first['results'] == [{'number': 1, 'priority': 'High', 'action': 'verified'}]
    second = run_cli(monkeypatch, tmp_path, api, '--apply')
    assert [v['action'] for v in second['results']] == ['unchanged', 'verified']
    assert len(writes) == 3  # Field creation, then exactly two independent issue writes.


def test_permission_error_checkpoints_and_never_retries(monkeypatch, tmp_path):
    import json
    import subprocess

    calls = []

    def api(path, payload=None, **kwargs):
        calls.append(path)
        if path == 'user':
            return {'login': 'owner'}
        if path == 'user/issue-fields':
            raise subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 403: blocked')
        return [[ticket()]]

    with pytest.raises(SystemExit, match='403'):
        run_cli(monkeypatch, tmp_path, api, '--apply')
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['error'] == 'HTTP 403: blocked'
    assert calls.count('user/issue-fields') == 1
