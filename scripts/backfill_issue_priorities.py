"""Preview or backfill native Priority fields on imported GitHub issues.

Requires gh authentication, PyYAML, account Issue Fields write permission and
repository Issues write permission. Defaults to preview; never retries writes.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import yaml

LEVELS = ('High', 'Medium', 'Low')


def plan_priorities(issues: list[dict]) -> list[dict]:
    """Read only the importer's fenced original metadata, never narrative text."""
    result = []
    for issue in issues:
        body = issue.get('body') or ''
        if 'pull_request' in issue or not re.search(r'<!-- local-issue-migration:v1:[^\n]+ -->', body):
            continue
        match = re.search(r'<summary>Original metadata</summary>\s*(`{3,})yaml\n(.*?)\n\1\s*</details>', body, re.DOTALL)
        if not match:
            raise ValueError(f'Missing original priority metadata: #{issue["number"]}')
        # Legacy titles can contain unquoted colons. Read the single top-level
        # priority scalar without reinterpreting unrelated legacy YAML fields.
        lines = re.findall(r'^priority:[ \t]*([^\n]+)$', match[2], re.MULTILINE)
        if len(lines) != 1:
            raise ValueError(f'Missing or duplicate priority: #{issue["number"]}')
        priority = yaml.safe_load(lines[0])
        if priority not in LEVELS:
            raise ValueError(f'Unknown priority {priority!r}: #{issue["number"]}')
        result.append({'number': issue['number'], 'priority': priority})
    return result


def choose_action(values: list[dict], field_id: int, priority: str) -> str:
    """Skip existing values, including intentional changes since migration."""
    for value in values:
        if value['issue_field_id'] == field_id:
            current = (value.get('single_select_option') or {}).get('name', value.get('value'))
            return 'unchanged' if current == priority else 'conflict'
    return 'set'


def api(path: str, payload: dict | None = None, *, paginate: bool = False) -> object:
    """Call gh without shell interpolation; propagate failures without retry."""
    args = ['gh', 'api', '--hostname', 'github.com', '-H',
            'X-GitHub-Api-Version: 2026-03-10', path]
    if paginate:
        args += ['--paginate', '--slurp']
    if payload is not None:
        args += ['--method', 'POST', '--input', '-']
    response = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                              capture_output=True, text=True, check=True, timeout=120)
    return json.loads(response.stdout)


def main() -> None:
    """Build a preview or apply a small, slowly paced resumable batch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=25, help='Maximum issue writes per invocation')
    parser.add_argument('--delay', type=float, default=15, help='Seconds between writes (minimum 15)')
    args = parser.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', args.repo) or args.limit < 1 or args.delay < 15:
        parser.error('Use OWNER/REPO, a positive limit, and a delay of at least 15 seconds')
    report = {'repo': args.repo, 'mode': 'apply' if args.apply else 'preview', 'results': []}

    def checkpoint() -> None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_suffix(args.report.suffix + '.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(args.report)

    try:
        pages = api(f'repos/{args.repo}/issues?state=all&per_page=100', paginate=True)
        plan = plan_priorities([issue for page in pages for issue in page])
        report['plan'] = plan
        checkpoint()
        if not args.apply:
            print(f'Preview: {len(plan)} priorities; report: {args.report}')
            return
        owner = api('user')['login']
        if owner.casefold() != args.repo.split('/')[0].casefold():
            raise ValueError('This utility supports repositories owned by the authenticated user')
        fields = api('user/issue-fields')
        matches = [field for field in fields if field['name'].casefold() == 'priority']
        if len(matches) > 1:
            raise ValueError('Multiple Priority fields; resolve ambiguity before applying')
        if matches:
            field = matches[0]
            if field['data_type'] != 'single_select' or not set(LEVELS).issubset(
                    {option['name'] for option in field.get('options', [])}):
                raise ValueError('Existing Priority field must offer High, Medium and Low')
        else:
            field = api('user/issue-fields', {
                'name': 'Priority', 'description': 'Work scheduling priority',
                'data_type': 'single_select', 'visibility': 'all',
                'options': [{'name': name, 'color': color, 'priority': rank}
                            for rank, (name, color) in enumerate(
                                zip(LEVELS, ('red', 'yellow', 'green')), 1)]})
            time.sleep(args.delay)
        writes = 0
        for item in plan:
            path = f'repos/{args.repo}/issues/{item["number"]}/issue-field-values'
            pages = api(path + '?per_page=100', paginate=True)
            action = choose_action([value for page in pages for value in page], field['id'], item['priority'])
            if action == 'set':
                if writes >= args.limit:
                    break
                api(path, {'issue_field_values': [{'field_id': field['id'], 'value': item['priority']}]})
                writes += 1
                time.sleep(args.delay)
                pages = api(path + '?per_page=100', paginate=True)
                if choose_action([v for page in pages for v in page], field['id'], item['priority']) != 'unchanged':
                    raise ValueError(f'Priority verification failed: #{item["number"]}')
                action = 'verified'
            report['results'].append(dict(item, action=action))
            checkpoint()
        print(f'{writes} priorities updated; rerun to continue. Report: {args.report}')
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as error:
        report['error'] = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        checkpoint()
        raise SystemExit(f'Stopped without retry: {report["error"]}') from error


if __name__ == '__main__':
    main()
