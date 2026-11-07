#!/usr/bin/env python3
"""Audit generated-chart components or bound campaign evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.chart_engine_audit import (
    run_engine_audit,
    supported_audit_policies,
    validate_engine_report,
)


def _cohort_output_collides(args: argparse.Namespace, prepared: Path | None = None) -> bool:
    """Harvest protected paths before validation, including failed receipts."""
    output = args.output.resolve()
    files = [path for path in (args.contract, args.engine_report, args.source_inputs) if path is not None]
    roots = [path for path in (args.source_stats_dir, args.reproduced_dir) if path is not None]
    if args.season_dir is not None:
        files.extend(path for path in args.season_dir.rglob("*") if path.is_file())
    if prepared is not None:
        files.append(prepared)
        roots.append(prepared.parent)
        try:
            data = json.loads(prepared.read_text())
            if isinstance(data, dict):
                binding, paths, execution = (data.get(name, {}) for name in ("binding", "source_paths", "execution"))
                if isinstance(binding, dict):
                    if isinstance(binding.get("bundle_dir"), str):
                        roots.append(Path(binding["bundle_dir"]))
                    if isinstance(binding.get("generation_files"), dict):
                        files.extend(ROOT / name for name in binding["generation_files"] if isinstance(name, str))
                if isinstance(paths, dict):
                    roots.extend(Path(paths[name]) for name in ("stats_dir", "reproduced_dir")
                                 if isinstance(paths.get(name), str))
                    if isinstance(paths.get("input_files"), dict):
                        files.extend(Path(path) for path in paths["input_files"].values() if isinstance(path, str))
                if isinstance(execution, dict) and isinstance(execution.get("log_path"), str):
                    files.append(Path(execution["log_path"]))
                if isinstance(data.get("gate_input_inventory"), str):
                    files.append(Path(data["gate_input_inventory"]))
        except (ValueError, OSError):
            pass  # The strict receipt reader reports malformed/missing evidence.
    if args.source_inputs is not None:
        try:
            paths = json.loads(args.source_inputs.read_text())
            if isinstance(paths, dict):
                files.extend(args.source_inputs.parent / path for path in paths.values() if isinstance(path, str))
        except (ValueError, OSError):
            pass
    return any(output == path.resolve() for path in files) or any(output.is_relative_to(path.resolve()) for path in roots)


def _implementation_output_collides(output: Path) -> bool:
    output = output.resolve()
    roots = ("paydirt", "tests", "scripts", "config", "docs", "paydirt-web", "seasons", ".github", ".git")
    files = [ROOT / name for name in ("AGENTS.md", "pyproject.toml", "README.md", ".gitignore", ".gitattributes", ".gitmodules")]
    files.extend(ROOT.glob("*.py"))
    files.extend(ROOT.glob("*.spec"))
    return (any(output.is_relative_to((ROOT / name).resolve()) for name in roots)
            or any(output == path.resolve() for path in files))


def _visual_capture_result(args: argparse.Namespace) -> dict:
    """Read both bound inputs and validate a saved capture without running games."""
    import hashlib

    from paydirt.chart_release_gate import (
        _strict_json_object,
        audit_readiness_freeze,
        audit_visual_capture_evidence,
        audit_visual_content_evidence,
        audit_visual_selection_evidence,
    )

    if args.visual_capture is None or args.freeze is None:
        raise ValueError("Visual-capture validation requires --visual-capture and --freeze")
    if args.visual_selection is not None and args.visual_content is None:
        raise ValueError("Visual-selection validation requires --visual-content")
    output = args.output.resolve()
    if args.output.exists() or args.output.is_symlink() or not output.is_relative_to(ROOT / ".ai-audits"):
        raise ValueError("Visual-capture output requires a new file under ignored .ai-audits/")
    freeze_bytes, evidence_bytes = args.freeze.read_bytes(), args.visual_capture.read_bytes()
    freeze, evidence = _strict_json_object(freeze_bytes), _strict_json_object(evidence_bytes)
    preflight = audit_readiness_freeze(ROOT, freeze)
    if not preflight["passed"]:
        raise ValueError("Visual-capture freeze preflight failed: " + "; ".join(preflight["errors"]))
    for entry in freeze["cohorts"].values():
        protected = [(ROOT / entry["season_dir"]).resolve(), (ROOT / entry["contract"]["path"]).resolve().parent]
        protected.extend((ROOT / ref["path"]).resolve().parent for ref in entry["source_inputs"].values())
        if any(output.is_relative_to(path) for path in protected):
            raise ValueError("Visual-capture output cannot be inside candidate or source inputs")
    if (any(value is not None for value in (
        args.season_dir, args.contract, args.campaign_bundle, args.engine_report,
        args.source_inputs, args.source_stats_dir, args.reproduced_dir,
    )) or args.engine_only or args.attempt_end_zone_interception_returns
            or args.policy != "chart-focused" or args.seed != 20261108
            or args.repetitions != 64 or args.workers != 4):
        raise ValueError("Visual-capture validation cannot be combined with cohort or campaign options")
    content_bytes = selection_bytes = None
    if args.visual_selection is not None:
        content_bytes = args.visual_content.read_bytes()
        selection_bytes = args.visual_selection.read_bytes()
        result = audit_visual_selection_evidence(ROOT, freeze, evidence, _strict_json_object(content_bytes),
                                                 _strict_json_object(selection_bytes))
    elif args.visual_content is not None:
        content_bytes = args.visual_content.read_bytes()
        result = audit_visual_content_evidence(ROOT, freeze, evidence, _strict_json_object(content_bytes))
    else:
        result = audit_visual_capture_evidence(ROOT, freeze, evidence)
    result["input_files"] = {
        "freeze": {"path": str(args.freeze.resolve()), "sha256": hashlib.sha256(freeze_bytes).hexdigest()},
        "captures": {"path": str(args.visual_capture.resolve()), "sha256": hashlib.sha256(evidence_bytes).hexdigest()},
    }
    if content_bytes is not None:
        result["input_files"]["content"] = {"path": str(args.visual_content.resolve()),
                                           "sha256": hashlib.sha256(content_bytes).hexdigest()}
        if args.visual_content.read_bytes() != content_bytes:
            result["errors"].append("Visual-content input file changed during validation")
    if selection_bytes is not None:
        result["input_files"]["selection"] = {"path": str(args.visual_selection.resolve()),
                                             "sha256": hashlib.sha256(selection_bytes).hexdigest()}
        if args.visual_selection.read_bytes() != selection_bytes:
            result["errors"].append("Visual-selection input file changed during validation")
    if args.freeze.read_bytes() != freeze_bytes or args.visual_capture.read_bytes() != evidence_bytes:
        result["errors"].append("Visual-capture input file changed during validation")
    result["passed"] = not result["errors"]
    for flag in ("candidate_content_validated", "selection_validated"):
        if flag in result:
            result[flag] = result[flag] and result["passed"]
    return result


def _reference_corpus_result(args: argparse.Namespace) -> dict:
    """Read stable-candidate evidence and keep all reference-derived output local."""
    import hashlib

    from paydirt.chart_release_gate import (
        _strict_json_object,
        audit_reference_context_evidence,
        audit_reference_corpus_evidence,
        audit_reference_paired_evidence,
        audit_reference_weighted_evidence,
    )

    if args.freeze is None or args.reference_corpus is None:
        raise ValueError("Reference comparison requires --reference-corpus and --freeze")
    if sum((args.reference_weighted, args.reference_contexts, args.reference_paired is not None)) > 1:
        raise ValueError("Choose one reference comparison component")
    if (any(value is not None for value in (
        args.season_dir, args.contract, args.campaign_bundle, args.engine_report,
        args.source_inputs, args.source_stats_dir, args.reproduced_dir,
        args.visual_capture, args.visual_content, args.visual_selection,
    )) or args.engine_only or args.attempt_end_zone_interception_returns
            or args.policy != "chart-focused" or args.seed != 20261108
            or args.repetitions != 64 or args.workers != 4):
        raise ValueError("Reference preflight cannot be combined with cohort, campaign or visual options")

    def output_path() -> Path:
        path = args.output.absolute()
        if (args.output.exists() or args.output.is_symlink()
                or not path.is_relative_to(ROOT / ".ai-audits/chart-reference-comparison")
                or any(parent.is_symlink() for parent in (path, *path.parents) if parent.is_relative_to(ROOT))
                or path != path.resolve()):
            raise ValueError("Reference output requires a new canonical local file under ignored .ai-audits/chart-reference-comparison/")
        return path

    output = output_path()
    freeze_bytes, declaration_bytes = args.freeze.read_bytes(), args.reference_corpus.read_bytes()
    freeze, evidence = _strict_json_object(freeze_bytes), _strict_json_object(declaration_bytes)
    paired_bytes = args.reference_paired.read_bytes() if args.reference_paired is not None else None
    paired = _strict_json_object(paired_bytes) if paired_bytes is not None else None
    protected = [args.freeze.resolve(), args.reference_corpus.resolve()]
    if paired is not None:
        protected.append(args.reference_paired.resolve())
        for side in ("generated", "reference"):
            binding = paired.get(side)
            if isinstance(binding, dict) and isinstance(binding.get("path"), str):
                protected.append((ROOT / binding["path"]).resolve())
    roots = []
    corpus = evidence.get("corpus")
    if isinstance(corpus, dict) and isinstance(corpus.get("directory"), str):
        roots.append((ROOT / corpus["directory"]).resolve())
    cohorts = freeze.get("cohorts", {})
    if isinstance(cohorts, dict):
        for entry in cohorts.values():
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("season_dir"), str):
                roots.append((ROOT / entry["season_dir"]).resolve())
            references = [entry.get("contract")]
            if isinstance(entry.get("source_inputs"), dict):
                references.extend(entry["source_inputs"].values())
            for ref in references:
                if isinstance(ref, dict) and isinstance(ref.get("path"), str):
                    roots.append((ROOT / ref["path"]).resolve().parent)
    for field in ("source_receipts", "training"):
        references = evidence.get(field, {})
        if not isinstance(references, dict):
            continue
        for ref in references.values():
            if isinstance(ref, dict) and isinstance(ref.get("path"), str):
                path = ROOT / ref["path"]
                roots.append(path.resolve().parent)
                if field == "source_receipts" and _cohort_output_collides(args, path):
                    raise ValueError("Reference output cannot overwrite prepared-source evidence")
    if output in protected or any(output.is_relative_to(path) for path in roots):
        raise ValueError("Reference output cannot be inside corpus, candidate or source inputs")
    if paired is not None:
        result = audit_reference_paired_evidence(ROOT, freeze, evidence, paired)
    else:
        audit = (audit_reference_context_evidence if args.reference_contexts else
                 audit_reference_weighted_evidence if args.reference_weighted else audit_reference_corpus_evidence)
        result = audit(ROOT, freeze, evidence)
    result["input_files"] = {
        "freeze": {"path": str(args.freeze.resolve()), "sha256": hashlib.sha256(freeze_bytes).hexdigest()},
        "declaration": {"path": str(args.reference_corpus.resolve()), "sha256": hashlib.sha256(declaration_bytes).hexdigest()},
    }
    originals = [("freeze", args.freeze, freeze_bytes), ("declaration", args.reference_corpus, declaration_bytes)]
    if paired_bytes is not None:
        result["input_files"]["paired"] = {"path": str(args.reference_paired.resolve()),
                                          "sha256": hashlib.sha256(paired_bytes).hexdigest()}
        originals.append(("paired", args.reference_paired, paired_bytes))
    for name, path, original in originals:
        if (any(parent.is_symlink() for parent in (path, *path.parents) if parent.is_relative_to(ROOT))
                or path.read_bytes() != original):
            result["errors"].append(f"Reference {name} file changed during validation")
    output_path()
    result["passed"] = not result["errors"]
    result["corpus_validated"] = result["corpus_validated"] and result["passed"]
    if args.reference_weighted:
        result["weighted_validated"] = result["weighted_validated"] and result["passed"]
    if args.reference_contexts:
        result["contexts_validated"] = result["contexts_validated"] and result["passed"]
    if args.reference_paired is not None:
        result["paired_validated"] = result["paired_validated"] and result["passed"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season-dir", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaign-bundle", type=Path,
                        help="Validate bound campaign files without starting games; component evidence only")
    parser.add_argument("--visual-capture", type=Path,
                        help="Validate bound browser captures only; selection/content/review remain separate")
    parser.add_argument("--visual-content", type=Path, help="Compare saved candidate/API/DOM content with --visual-capture")
    parser.add_argument("--visual-selection", type=Path, help="Validate bound charter representatives with --visual-content")
    parser.add_argument("--reference-corpus", type=Path, help="Validate stable dependencies and private corpus census only")
    parser.add_argument("--reference-weighted", action="store_true", help="Add exact pre-state four-combination reference diagnostics")
    parser.add_argument("--reference-contexts", action="store_true", help="Collect complete matched stateful context diagnostics")
    parser.add_argument("--reference-paired", type=Path, help="Validate bound complete paired reference campaign reports; starts no games")
    parser.add_argument("--freeze", type=Path, help="Frozen implementation and source inventory for saved evidence")
    parser.add_argument("--engine-report", type=Path)
    parser.add_argument("--source-inputs", type=Path,
                        help="JSON mapping manifest input labels to local source files")
    parser.add_argument("--source-stats-dir", type=Path,
                        help="Normalized source statistics checked independently of the manifest")
    parser.add_argument("--reproduced-dir", type=Path,
                        help="Charts independently regenerated from the declared inputs")
    parser.add_argument("--engine-only", action="store_true",
                        help="Collect evidence only; does not certify a release")
    parser.add_argument("--repetitions", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--policy", choices=supported_audit_policies(), default="chart-focused")
    parser.add_argument("--attempt-end-zone-interception-returns", action="store_true",
                        help="Both teams attempt own-end-zone INT returns; default automatic touchback")
    args = parser.parse_args(argv)
    output_allowed = True
    try:
        if _implementation_output_collides(args.output):
            output_allowed = False
            raise ValueError("Audit output must be separate from implementation, tests, configuration and guides")
        if args.reference_corpus is not None or args.reference_weighted or args.reference_contexts or args.reference_paired is not None:
            output_allowed = False
            result = _reference_corpus_result(args)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as stream:
                stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
            print(f"{'PASS' if result['passed'] else 'FAIL'}: {args.output}", flush=True)
            return 0 if result["passed"] else 1
        if any(value is not None for value in (args.visual_capture, args.freeze, args.visual_content, args.visual_selection)):
            output_allowed = False
            result = _visual_capture_result(args)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as stream:
                stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
            print(f"{'PASS' if result['passed'] else 'FAIL'}: {args.output}", flush=True)
            return 0 if result["passed"] else 1
        if args.campaign_bundle:
            from paydirt.chart_release_gate import audit_campaign_bundle_file
            result = audit_campaign_bundle_file(args.campaign_bundle)
            output = args.output.resolve()
            binding = result["binding"]
            if (output == args.campaign_bundle.resolve() or str(output) in binding["input_paths"]
                    or any(output.is_relative_to(Path(candidate)) for candidate in binding["candidate_paths"])):
                output_allowed = False
                raise ValueError("Campaign output must not overwrite bundle inputs or candidate charts")
            if (any(value is not None for value in (
                args.season_dir, args.contract, args.engine_report, args.source_inputs,
                args.source_stats_dir, args.reproduced_dir,
            )) or args.engine_only or args.attempt_end_zone_interception_returns
                    or args.policy != "chart-focused" or args.seed != 20261108
                    or args.repetitions != 64 or args.workers != 4):
                raise ValueError("--campaign-bundle cannot be combined with cohort execution options")
            passed = result["passed"]
        else:
            if _cohort_output_collides(args):
                output_allowed = False
                raise ValueError("Cohort output must not overwrite chart or evidence inputs")
            if args.season_dir is None or args.contract is None:
                raise ValueError("Cohort audit requires --season-dir and --contract")
            contract = json.loads(args.contract.read_text())
            source_options = {}
            if not args.engine_only:
                source_flags = (args.source_inputs, args.source_stats_dir, args.reproduced_dir)
                prepared = ROOT / ".ai-audits/chart-sources" / str(contract.get("season")) / "source.json"
                if _cohort_output_collides(args, prepared):
                    output_allowed = False
                    raise ValueError("Cohort output must not overwrite prepared source evidence or generation code")
                if all(path is None for path in source_flags) and prepared.is_file():
                    from paydirt.chart_source_bundle import prepared_source_options
                    source_options = prepared_source_options(prepared, args.season_dir, args.contract)
                elif any(path is None for path in source_flags):
                    raise ValueError(
                        "Component gate requires --source-inputs, --source-stats-dir and --reproduced-dir "
                        "or current verified .ai-audits/chart-sources/SEASON/source.json preparation"
                    )
                else:
                    paths = json.loads(args.source_inputs.read_text())
                    if (not isinstance(paths, dict) or not paths
                            or any(not isinstance(key, str) or not key
                                   or not isinstance(value, str) or not value
                                   for key, value in paths.items())):
                        raise ValueError("Source input inventory requires nonempty label/path strings")
                    source_options = {
                        "input_files": {key: args.source_inputs.parent / value for key, value in paths.items()},
                        "stats_dir": args.source_stats_dir,
                        "reproduced_dir": args.reproduced_dir,
                    }
            schedule = [(game["away"], game["home"]) for game in contract["schedule"]]
            if args.engine_report:
                report = json.loads(args.engine_report.read_text())
            else:
                print(f"Running {args.repetitions} source-schedule repetitions, "
                      f"{len(schedule)} games each, policy={args.policy}", flush=True)
                report = run_engine_audit(args.season_dir, schedule,
                                          repetitions=args.repetitions, seed=args.seed,
                                          policy=args.policy, workers=args.workers,
                                          attempt_end_zone_interception_returns=args.attempt_end_zone_interception_returns)
            if (report.get("metadata", {}).get("attempt_end_zone_interception_returns")
                    is not args.attempt_end_zone_interception_returns):
                raise ValueError("Evidence interception return policy differs from requested audit option")
            if args.engine_only:
                result = report
                policy = report.get("metadata", {}).get("policy", args.policy)
                minimum = 1000 if policy == "chart-focused" else 128 if policy in {"hard", "balanced"} else 16
                minimum_repetitions = 64 if policy == "chart-focused" else 8 if policy in {"hard", "balanced"} else 1
                result["validation"] = validate_engine_report(
                    report, contract, args.season_dir, minimum_team_games=minimum,
                    minimum_repetitions=minimum_repetitions,
                    require_fit=policy == "chart-focused",
                )
                result["release_certified"] = False
                passed = result["validation"]["passed"]
            else:
                from paydirt.chart_release_gate import audit_release
                result = audit_release(args.season_dir, contract, report, **source_options)
                passed = result["passed"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        print(f"{'PASS' if passed else 'FAIL'}: {args.output}", flush=True)
        return 0 if passed else 1
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        failure = {"passed": False, "release_certified": False,
                   "errors": [f"Audit execution failed: {error}"]}
        try:
            if output_allowed:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(failure, indent=2) + "\n")
        except OSError as output_error:
            print(f"Cannot preserve failure evidence: {output_error}", file=sys.stderr)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
