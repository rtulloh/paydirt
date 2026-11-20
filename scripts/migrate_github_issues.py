#!/usr/bin/env python3
"""Import YAML-front-matter Markdown tickets; offline preview unless --apply.

Standalone developer tool: Python 3.10+, PyYAML and (for apply) authenticated gh.
Copy this file to another repository or point --source-root at its checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit

import yaml


@dataclass(frozen=True)
class Issue:
    """An immutable local ticket, including its original metadata and history."""

    id: str
    title: str
    status: str
    path: str
    front: str
    body: str
    sha256: str


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate metadata keys instead of silently losing information."""


def unique_mapping(loader: UniqueLoader, node: yaml.MappingNode) -> dict:
    """Decode a YAML mapping without duplicate keys."""
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"Invalid or duplicate metadata key: {key!r}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate_repo(repo: str) -> None:
    """Require an explicit GitHub.com OWNER/REPO, never infer a destination."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repo):
        raise ValueError("--repo must be OWNER/REPO on github.com")
    if repo.split('/')[1] in {'.', '..'}:
        raise ValueError("Invalid repository name")


def load_issues(source_root: Path, issues_dir: Path) -> list[Issue]:
    """Validate every ticket before any remote write; README files are not tickets."""
    root = source_root.resolve(strict=True)
    folder = root / issues_dir
    if folder.is_symlink() or not folder.is_dir() or not folder.resolve().is_relative_to(root):
        raise ValueError("Issue directory must be a real directory inside --source-root")
    for path in (folder, *folder.parents):
        if path == root:
            break
        if path.is_symlink():
            raise ValueError(f"Symlink in source path: {path}")
    result = []
    seen = set()
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not migrated: {path}")
        if not path.is_file() or path.suffix.lower() != '.md' or path.name.lower() == 'readme.md':
            continue
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig').replace('\r\n', '\n')
        match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            raise ValueError(f"Missing YAML front matter: {path}")
        front, body = match.groups()
        try:
            try:
                fields = yaml.load(front, Loader=UniqueLoader)
            except yaml.YAMLError:
                # The local trackers also accept literal colons in an unquoted
                # title. Repair only that legacy scalar in the parsing view.
                parse_front = re.sub(
                    r"(?m)^title: (?!['\"|>])(.+)$",
                    lambda m: 'title: ' + json.dumps(m[1]), front)
                fields = yaml.load(parse_front, Loader=UniqueLoader)
        except yaml.YAMLError as error:
            raise ValueError(f"Invalid YAML: {path}: {error}") from error
        if not isinstance(fields, dict):
            raise TypeError(f"Invalid metadata mapping: {path}")
        local_id, title, status = (fields.get(k) for k in ('id', 'title', 'status'))
        if not isinstance(local_id, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', local_id):
            raise ValueError(f"Invalid issue ID: {path}")
        if local_id in seen:
            raise ValueError(f"Duplicate local issue ID: {local_id}")
        if not isinstance(title, str) or not title.strip() or '\n' in title:
            raise ValueError(f"Invalid title: {path}")
        if len(f'[{local_id}] {title}') > 256:
            raise ValueError(f"GitHub title exceeds 256 characters: {path}")
        if not isinstance(status, str) or status not in {'open', 'resolved', 'closed'} or not body.strip():
            raise ValueError(f"Invalid status or empty body: {path}")
        issue = Issue(local_id, title, status, path.relative_to(root).as_posix(),
                      front, body, hashlib.sha256(raw).hexdigest())
        seen.add(local_id)
        result.append(issue)
    if not result:
        raise ValueError(f"No issue Markdown files found in {folder}")
    return result


def marker(issue: Issue, namespace: str) -> str:
    """A stable remote key makes reruns independent of the local report file."""
    key = hashlib.sha256(namespace.encode()).hexdigest()[:24]
    return f'<!-- local-issue-migration:v1:{key}:{issue.id} -->'


def blob_url(repo: str, ref: str, path: str) -> str:
    """Encode repository-relative paths, retaining fragments where supplied."""
    return f'https://github.com/{repo}/blob/{quote(ref, safe="")}/{quote(path, safe="/")}'


def render_body(issue: Issue, repo: str, namespace: str, ref: str) -> str:
    """Preserve metadata/history and make ordinary relative Markdown links usable."""
    def destination(value: str) -> str:
        angle = value.startswith('<') and value.endswith('>')
        target = value[1:-1] if angle else value
        parsed = urlsplit(target)
        if not target or parsed.scheme or parsed.netloc or target.startswith(('#', '/')):
            return value
        path = posixpath.normpath(posixpath.join(posixpath.dirname(issue.path), parsed.path))
        if path == '..' or path.startswith('../'):
            return value  # Preserve, but never fabricate an out-of-repository blob link.
        url = blob_url(repo, ref, path)
        if parsed.query:
            url += '?' + parsed.query
        if parsed.fragment:
            url += '#' + parsed.fragment
        return '<' + url + '>' if angle else url

    def links(text: str) -> str:
        text = re.sub(r'(!?\[[^\]\n]*\]\()(<[^>\n]*>|[^\s)]+)',
                      lambda m: m[1] + destination(m[2]), text)
        return re.sub(r'(?m)^(\s{0,3}\[[^\]\n]+\]:\s*)(<[^>\n]*>|\S+)',
                      lambda m: m[1] + destination(m[2]), text)

    lines = []
    code_fence = None
    for line in issue.body.splitlines(keepends=True):
        fence_match = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if code_fence:
            lines.append(line)
            if fence_match and fence_match[1][0] == code_fence[0] and len(fence_match[1]) >= len(code_fence):
                code_fence = None
        elif fence_match:
            code_fence = fence_match[1]
            lines.append(line)
        elif line.startswith(('    ', '\t')):
            lines.append(line)
        else:
            segments = re.split(r'(`+[^`]*`+)', line)
            lines.append(''.join(part if n % 2 else links(part)
                                 for n, part in enumerate(segments)))
    body = ''.join(lines)
    fence = '`' * max(3, 1 + max((len(x) for x in re.findall(r'`+', issue.front)), default=0))
    pending = 'Resolved locally; awaiting play-test confirmation. Kept open on GitHub.\n\n' \
        if issue.status == 'resolved' else ''
    return (
        marker(issue, namespace) + '\n' + f'<!-- local-issue-sha256:{issue.sha256} -->\n\n'
        f'Imported local issue **{issue.id}** (original status: **{issue.status}**).\n\n'
        + pending + f'[Original source]({blob_url(repo, ref, issue.path)})\n\n'
        'Historical dates and comments below are copied records, not GitHub creation '
        'timestamps or impersonated authors.\n\n<details>\n<summary>Original metadata</summary>\n\n'
        + fence + 'yaml\n' + issue.front + '\n' + fence + '\n\n</details>\n'
        + body
    )


def split_body(body: str, limit: int = 60000) -> list[str]:
    """Split without discarding characters; leave room for history-comment headers."""
    parts = []
    while len(body) > limit:
        boundary = body.rfind('\n', 0, limit)
        cut = boundary + 1 if boundary >= limit // 2 else limit
        parts.append(body[:cut])
        body = body[cut:]
    parts.append(body)
    return parts


def history_marker(issue: Issue, namespace: str, part: int) -> str:
    """Derive independently resumable history-comment identifiers."""
    return marker(issue, namespace).replace('local-issue-migration:', 'local-issue-history:').replace(
        ' -->', f':{part} -->')


def history_body(issue: Issue, namespace: str, part: int, total: int, text: str) -> str:
    """Keep import bookkeeping separate from the original history chunk."""
    return (history_marker(issue, namespace, part) + '\n'
            + f'<!-- local-issue-sha256:{issue.sha256} -->\n\n'
            + f'Imported history part {part}/{total} for {issue.id}.\n\n' + text)


class GhClient:
    """GitHub REST via gh, using JSON stdin and a delay between mutation requests."""

    def __init__(self, repo: str) -> None:
        validate_repo(repo)
        self.repo = repo
        self.last_write = 0.0

    def api(self, path: str, method: str = 'GET', payload: dict | None = None,
            *, paginate: bool = False) -> object:
        """Stop on API errors; never blindly retry an uncertain issue creation."""
        args = ['gh', 'api', '--hostname', 'github.com', '--method', method,
                f'repos/{self.repo}/{path}']
        if paginate:
            args += ['--paginate', '--slurp']
        if payload is not None:
            time.sleep(max(0.0, 1.1 - (time.monotonic() - self.last_write)))
            self.last_write = time.monotonic()
            args += ['--input', '-']
        result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True, check=True, timeout=120)
        return json.loads(result.stdout)

    def list_issues(self) -> list[dict]:
        """Include closed issues, follow every page, and ignore pull requests."""
        pages = self.api('issues?state=all&per_page=100', paginate=True)
        return [item for page in pages for item in page if 'pull_request' not in item]

    def ensure_labels(self, names: list[str]) -> None:
        """Create only missing migration-status labels; preserve other labels."""
        pages = self.api('labels?per_page=100', paginate=True)
        existing = {item['name'] for page in pages for item in page}
        for name in names:
            if name not in existing:
                self.api('labels', 'POST', {'name': name, 'color': 'd4c5f9',
                         'description': 'Original local issue status at migration'})

    def create_issue(self, title: str, body: str, label: str) -> dict:
        """Create with a durable marker in the initial request."""
        return self.api('issues', 'POST', {'title': title, 'body': body, 'labels': [label]})

    def list_comments(self, number: int) -> list[dict]:
        """Find every previously imported history part, including paginated ones."""
        pages = self.api(f'issues/{number}/comments?per_page=100', paginate=True)
        return [item for page in pages for item in page]

    def create_comment(self, number: int, body: str) -> None:
        """Import a history chunk with its marker in the initial request."""
        self.api(f'issues/{number}/comments', 'POST', {'body': body})

    def close_issue(self, number: int) -> None:
        """Preserve local closed state after successful creation."""
        self.api(f'issues/{number}', 'PATCH', {'state': 'closed', 'state_reason': 'completed'})


def migrate(issues: list[Issue], repo: str, *, namespace: str = 'local-markdown',
            ref: str = 'main', client: GhClient | None = None,
            checkpoint: Callable[[list[dict]], None] | None = None) -> list[dict]:
    """Preflight the entire batch; resume without replacing remote issue content."""
    validate_repo(repo)
    if not namespace.strip() or not ref.strip():
        raise ValueError('Namespace and source ref must be nonempty')
    prepared = [(i, split_body(render_body(i, repo, namespace, ref))) for i in issues]
    remote = client.list_issues() if client else []
    existing = {}
    imported_parts = {}
    for issue, parts in prepared:
        matches = [item for item in remote if marker(issue, namespace) in (item.get('body') or '')]
        if len(matches) > 1:
            raise ValueError(f'Duplicate remote migration markers: {issue.id}')
        if matches:
            item = matches[0]
            if f'<!-- local-issue-sha256:{issue.sha256} -->' not in (item.get('body') or ''):
                raise ValueError(f'Local source changed since import: {issue.id}; reconcile manually')
            existing[issue.id] = item
            comments = client.list_comments(item['number']) if len(parts) > 1 else []
            for part in range(2, len(parts) + 1):
                found = [c for c in comments if history_marker(issue, namespace, part) in (c.get('body') or '')]
                if len(found) > 1:
                    raise ValueError(f'Duplicate imported history part: {issue.id}/{part}')
                if found:
                    if f'<!-- local-issue-sha256:{issue.sha256} -->' not in found[0]['body']:
                        raise ValueError(f'Imported history source changed: {issue.id}/{part}')
                    imported_parts[(issue.id, part)] = True
    if client:
        client.ensure_labels(sorted({'local-status:' + i.status for i in issues}))
    result = []
    for issue, parts in prepared:
        item = existing.get(issue.id)
        action = 'existing' if item else ('created' if client else 'planned')
        if client and not item:
            item = client.create_issue(f'[{issue.id}] {issue.title}', parts[0], 'local-status:' + issue.status)
        record = {'id': issue.id, 'source': issue.path, 'sha256': issue.sha256,
                  'local_status': issue.status, 'action': action,
                  'history_parts_total': len(parts),
                  'history_parts_imported': 1 + sum((issue.id, p) in imported_parts for p in range(2, len(parts) + 1)) if client else 0,
                  'number': item['number'] if item else None,
                  'url': item['html_url'] if item else None,
                  'closure_pending': bool(client and issue.status == 'closed' and item['state'] != 'closed')}
        if not client:
            record['preview_body'] = parts[0]
            record['preview_history_comments'] = [history_body(issue, namespace, n, len(parts), text)
                                                  for n, text in enumerate(parts[1:], 2)]
        result.append(record)
        if checkpoint:
            checkpoint(result)
        if client:
            for part, text in enumerate(parts[1:], 2):
                if (issue.id, part) not in imported_parts:
                    client.create_comment(item['number'], history_body(issue, namespace, part, len(parts), text))
                    record['history_parts_imported'] += 1
                    if checkpoint:
                        checkpoint(result)
        if record['closure_pending']:
            client.close_issue(item['number'])
            record['closure_pending'] = False
            if checkpoint:
                checkpoint(result)
    return result


def main(argv: list[str] | None = None) -> int:
    """Preview locally, or explicitly apply to the specified repository."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='Explicit GitHub.com OWNER/REPO destination')
    parser.add_argument('--source-root', type=Path, default=Path.cwd())
    parser.add_argument('--issues-dir', type=Path, default=Path('docs/dev-notes/issues'))
    parser.add_argument('--namespace', default='local-markdown', help='Keep stable across reruns')
    parser.add_argument('--source-ref', default='main', help='Branch/tag/commit for source links')
    parser.add_argument('--report', type=Path, help='JSON preview or resumable ID-to-URL report')
    parser.add_argument('--apply', action='store_true', help='Create GitHub issues and close local closed ones')
    args = parser.parse_args(argv)
    if args.apply and args.report is None:
        parser.error('--apply requires --report PATH for the migration mapping')
    try:
        issues = load_issues(args.source_root, args.issues_dir)
        if args.report and args.report.resolve() in {
                (args.source_root / i.path).resolve() for i in issues}:
            raise ValueError('Report must not overwrite a source issue')
        def save(records: list[dict]) -> None:
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                temporary = args.report.with_name(args.report.name + '.tmp')
                temporary.write_text(json.dumps({'repo': args.repo, 'namespace': args.namespace,
                                     'mode': 'apply' if args.apply else 'preview',
                                     'issues': records}, indent=2) + '\n', encoding='utf-8')
                os.replace(temporary, args.report)
        records = migrate(issues, args.repo, namespace=args.namespace, ref=args.source_ref,
                          client=GhClient(args.repo) if args.apply else None, checkpoint=save)
        counts = {state: sum(i.status == state for i in issues) for state in ['open', 'resolved', 'closed']}
        print(json.dumps({'mode': 'apply' if args.apply else 'preview', 'repo': args.repo,
                          'counts': counts, 'total': len(records),
                          'report': str(args.report) if args.report else None}, indent=2))
        return 0
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(f'Migration stopped: {detail}\nNo automatic retry. Correct the cause and rerun '
              'with the same repo/namespace; remote markers prevent duplicate imports.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
