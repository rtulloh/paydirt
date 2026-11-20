# Migrate Local Issues to GitHub

[Documentation index](README.md) · [Agent issue workflow](../AGENTS.md#issue-tracking)

`scripts/migrate_github_issues.py` is a standalone developer utility. It imports
every Markdown ticket under an issue directory, including open, resolved and
closed tickets. It works with Paydirt and Bowl Bound's YAML-front-matter formats;
it does not import the generated index, README files or retired-ID registries as
separate issues. Local files are never modified or deleted.

Paydirt's migration is complete: all 240 tickets were verified on GitHub, and the
local issue directory and generated tracker have been removed. The
[legacy-ID mapping](../.github/issue-migration.json) records their destinations.
Original files remain at commit `448f88e7cca2ff332d74b044e6273b604168321f`.
The Paydirt commands below describe the migration from a checkout containing those
sources; they cannot read the deleted directory in the current checkout. The
reusable script remains available for Bowl Bound and other repositories.

## Requirements

- Python 3.10 or later and PyYAML (`python3 -m pip install PyYAML`, preferably in
  a virtual environment).
- For applying: [GitHub CLI](https://cli.github.com/manual/gh_api), authenticated
  with `gh auth login`, and access to create issues, labels, comments and close
  imported issues in the destination repository. GitHub Issues must be enabled.
- Explicit destination `--repo OWNER/REPO`; the script does not infer or enable it.

## Preview Paydirt

From the Paydirt checkout, using a Python environment with the requirements:

```bash
python3 scripts/migrate_github_issues.py \
  --repo rtulloh/paydirt \
  --source-ref "$(git rev-parse HEAD)" \
  --report .ai-audits/github-migration/paydirt-preview.json
```

The default is **offline preview**: no `gh` invocation, network access, or GitHub
mutation. The JSON contains complete proposed bodies/history comments, original
IDs/statuses and source hashes. Review it before publishing, especially in a public
repository. Existing repo-local public-safety rules apply to issue content too.

## Import All Statuses

```bash
python3 scripts/migrate_github_issues.py \
  --repo rtulloh/paydirt \
  --source-ref "$(git rev-parse HEAD)" \
  --apply \
  --report .ai-audits/github-migration/paydirt-import.json
```

`--apply` explicitly creates issues and requires a report path. The report is
checkpointed after each successful operation and maps local IDs to GitHub numbers
and URLs. Do not run concurrent imports into the same repository/namespace.
Requests are sequential and mutation requests are paced to reduce rate-limit risk.
An API error stops the run; inspect the error and rerun after addressing it or
waiting out the rate limit. There is no blind retry of an uncertain creation.

| Local status | GitHub state | Original-status label |
| --- | --- | --- |
| open | Open | `local-status:open` |
| resolved | Open, awaiting play-test confirmation | `local-status:resolved` |
| closed | Closed after all history is imported | `local-status:closed` |

These labels describe status **at import**, not a live synchronization. For future
work use `awaiting-playtest` as described in AGENTS.md. Labels for imported statuses
are created if missing. Priority, tags, milestones/target release, commits,
related IDs and all other original metadata are retained verbatim in a collapsible
metadata block; the tool does not create corresponding milestones or assignees.

The title retains `[LOCAL-ID]`. Description, acceptance criteria and timestamped
comment history remain in the body. Bodies exceeding 60,000 characters continue
in numbered GitHub history comments without truncation. Those are imported history,
not backdated native comments: GitHub creation times/authorship belong to the
account running the script. Long Markdown constructs may span history parts;
the original source link remains available. Original file hashes are retained.
See GitHub's [issue API](https://docs.github.com/en/rest/issues/issues) for native
creation/update behavior.

Ordinary relative inline/image/reference Markdown links outside code are converted
to source-file links in the destination repository at `--source-ref` (default
`main`). Set a committed tag or commit hash for immutable references. Local issue
cross-links continue to the archived source files, not newly assigned GitHub issue
numbers. Raw HTML and unusual Markdown links are preserved rather than guessed.
Keep the source files available at that ref; a copied script cannot upload missing
referenced documents or images automatically.

## Resume Safely

Rerun the same command with the same repository and `--namespace` (default
`local-markdown`). The script reads **all pages of open and closed GitHub issues**
and checks durable import markers. It skips existing issue bodies and existing
history parts, preserving later community edits and comments. The report is useful
evidence, but duplicate detection does not depend on retaining it.

If creation succeeded but a later history/close request failed, rerunning finishes
the missing steps. Locally closed tickets that remain open on GitHub are closed
on rerun; locally open/resolved tickets never cause a remote issue to reopen.
This is an importer, not a bidirectional sync. Finish an interrupted migration
before beginning ordinary GitHub state changes on its imported tickets.

Changed local source hashes or duplicate remote import markers stop the entire
batch before new issues/labels are written. Reconcile changed records manually;
the script will not overwrite a discussion or silently create another copy.
Do not remove import markers or change namespaces to bypass duplicate detection.

## Reuse for Bowl Bound

Copy the single script to the other checkout, or run it directly from Paydirt with
an explicit source root. Substitute the actual destination from Bowl Bound's
configured Git remote:

```bash
python3 /path/to/paydirt/scripts/migrate_github_issues.py \
  --source-root /path/to/bowl_bound \
  --issues-dir docs/dev-notes/issues \
  --repo OWNER/REPO \
  --report /path/to/bowl_bound/.ai-audits/github-migration/preview.json
```

Review the preview, then add `--apply` and use an import-report path. The issue
directory may be elsewhere within the source root. Tickets need `id`, `title` and
`status: open|resolved|closed` in front matter followed by nonempty Markdown.
Wrapped YAML titles and legacy unquoted colon titles are supported. Invalid
records, duplicate IDs and symlinks fail preflight rather than being silently
omitted. There is no Paydirt package dependency or season-data requirement.

## Remove the Local Tracker After Verification

The owner's intended final state is GitHub Issues as the active tracker, with
local issue files and the generated local index removed from Git and disk.
The importer deliberately leaves that cleanup as a separate step after migration
verification; it does not delete files as a side effect of uploading.

Before importing, commit the complete issue sources and use that immutable commit
as `--source-ref`, as in the Paydirt examples. When using another source root,
obtain the commit from that checkout (`git -C /path/to/bowl_bound rev-parse HEAD`).
All imported sources and referenced documents must exist at the chosen commit.
This preserves source/history links after the files disappear from the default
branch. The default `main` source ref is unsuitable if you will delete its files.

After verifying every issue's number, state, complete history and source-to-URL
mapping, remove the migrated per-issue directory and generated index with
`git rm`. Update tracker links, agent workflow and local-tracker-specific tools
and tests in the same cleanup change so they reference GitHub or an optional
offline fallback. Do not rewrite Git history: the committed original records
remain available at the pinned source commit. Do not remove the User Guide,
screenshots or other reference/design documentation. Preserve the migration
mapping outside the deleted tracker directory for future cross-reference.
## Offline Drafts After Migration

Prefer GitHub Issues when connected. If access is unavailable, run
`python3 scripts/create_issue.py --help` and create drafts using `--prefix OFFLINE`.
The authoring helper stores tickets under ignored `.ai-audits/offline-issues/` and
regenerates `.ai-audits/offline-issue-tracker.md`; the index helper can also run
separately. Reconcile drafts with GitHub when access returns and retain their
URLs locally. These drafts do not recreate a committed issue tracker.

## Restore Native Priority Fields

The original migration preserves priority in each issue's Original metadata.
`scripts/backfill_issue_priorities.py` copies those values to a native, public
single-select Priority field with High, Medium and Low options. It supports
repositories owned by the authenticated personal account. GitHub CLI's token
needs account **Issue Fields: Read and write** to configure the field and repository
**Issues: Read and write** to populate it.

Preview the imported issues in any repository, including closed tickets:

```bash
python3 scripts/backfill_issue_priorities.py --repo rtulloh/paydirt \
  --report .ai-audits/github-migration/paydirt-priorities.json
```

After reviewing the plan, add `--apply`. The default batch updates at most 25 issues,
with a minimum 15-second delay between writes. Rerun to continue; existing values
are preserved, and conflicts with original priorities are reported instead of
overwritten. Each new priority is read back and verified. Unrelated issue fields
are preserved. A changed or incompatible existing Priority field stops the run.
The report checkpoints progress and stops on API errors without automatic retry.
After a secondary rate limit, allow GitHub's cooldown before restarting bulk writes;
avoid running this concurrently with another import or backfill.

For Bowl Bound, use the same script with `--repo rtulloh/bowl_bound` after its
migration completes. It reads original metadata from the imported GitHub bodies,
so it does not require local issue files. Reports remain ignored local evidence.
For ongoing scheduling, edit Priority in GitHub's issue sidebar; the imported
metadata remains a historical record rather than overriding later decisions.
