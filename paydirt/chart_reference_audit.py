"""Local normalized reference-corpus checks; never a historical accuracy score."""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from fractions import Fraction
from itertools import pairwise
from pathlib import Path
from typing import Any

from yaml import YAMLError, safe_load

from . import chart_audit
from .chart_loader import TeamChart, load_team_chart
from .play_resolver import DefenseType, PlayType
from .season_rules import load_season_rules


def _local_directory(root: Path, name: object) -> Path:
    if not isinstance(name, str) or not name:
        raise ValueError("Reference directory must be a canonical root-relative path")
    relative = Path(name)
    if (relative.is_absolute() or ".." in relative.parts or "\\" in name
            or relative.as_posix() != name or relative == Path(".")):
        raise ValueError("Reference directory must be a canonical root-relative path")
    path = root / relative
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent.is_relative_to(root)):
        raise ValueError("Reference directory cannot use symlinks")
    if not path.is_dir():
        raise ValueError("Reference directory is missing")
    return path


def reference_corpus_inventory(directory: Path) -> tuple[dict[str, str], list[str]]:
    """Census every regular file and directory, including empty extra folders."""
    files, directories = {}, []
    if any(path.is_symlink() for path in (directory, *directory.parents)) or not directory.is_dir():
        raise ValueError("Reference inputs must use a regular local directory")
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Reference inputs cannot use symlinks: {path.relative_to(directory)}")
        name = path.relative_to(directory).as_posix()
        if path.is_dir():
            directories.append(name)
        elif path.is_file():
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            raise ValueError(f"Unsupported reference filesystem entry: {name}")
    return files, directories


def audit_reference_corpus(
    root: Path, freeze: Mapping[str, Any], corpus: Mapping[str, Any], contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Check actual corpus bytes only after the caller validates stable dependencies."""
    errors: list[str] = []
    teams: dict[str, Any] = {}
    result: dict[str, Any] = {"passed": False, "errors": errors, "teams": teams,
                              "non_observation_proven": False, "rules_match": False}
    directory = None
    before = None
    try:
        if (not isinstance(corpus, Mapping) or set(corpus) != {
                "directory", "files", "teams", "partition_method",
        } or corpus["partition_method"] != "sha256-folder-order-alternating-v1"):
            raise ValueError("Requires the complete corpus and fixed partition declaration")
        names = contract.get("teams")
        mappings = corpus["teams"]
        if (not isinstance(names, dict) or len(names) != 28 or not isinstance(mappings, dict)
                or set(mappings) != set(names)):
            raise ValueError("Reference mappings must cover exactly all 28 frozen generated teams")
        ordered = sorted(names, key=lambda name: (
            hashlib.sha256(("paydirt-reference-partition-v1:" + name).encode()).hexdigest(), name))
        partitions = {name: "development" if index % 2 == 0 else "withheld"
                      for index, name in enumerate(ordered)}
        folders = []
        for name, entry in mappings.items():
            if (not isinstance(entry, dict) or set(entry) != {
                    "reference_folder", "partition", "inspected_before_freeze", "prior_use",
            } or not isinstance(entry["reference_folder"], str) or not entry["reference_folder"]
                    or entry["reference_folder"] in {".", ".."}
                    or Path(entry["reference_folder"]).name != entry["reference_folder"]
                    or "\\" in entry["reference_folder"]
                    or entry["partition"] != partitions[name]
                    or type(entry["inspected_before_freeze"]) is not bool
                    or not isinstance(entry["prior_use"], str) or not entry["prior_use"].strip()):
                raise ValueError(f"{name}: invalid mapping, fixed partition or prior-use declaration")
            folders.append(entry["reference_folder"])
        if len(set(folders)) != 28:
            raise ValueError("Reference folder mappings must be one to one")
        directory = _local_directory(root, corpus["directory"])
        for candidate in freeze["cohorts"].values():
            generated = (root / candidate["season_dir"]).resolve()
            if directory.is_relative_to(generated) or generated.is_relative_to(directory):
                raise ValueError("Reference corpus cannot overlap a frozen generated candidate")
        declared = corpus["files"]
        if (not isinstance(declared, dict) or not declared
                or any(not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest)
                       for digest in declared.values())):
            raise ValueError("Reference corpus needs an exact SHA-256 file inventory")
        before = reference_corpus_inventory(directory)
        result["files"], result["directories"] = before
        if before[0] != declared:
            raise ValueError("Reference file inventory differs from the declared bytes")
        if {name for name in before[1] if "/" not in name} != set(folders):
            raise ValueError("Reference directory census has omitted or extra team folders")
        for folder in folders:
            missing = {f"{folder}/{name}" for name in ("offense.csv", "defense.csv", "special.csv", "team.yaml")} - set(declared)
            if missing:
                raise ValueError("Reference team is incomplete: " + ", ".join(sorted(missing)))
        reference_rules = load_season_rules(directory).to_dict()
        generated_rules = load_season_rules(root / freeze["cohorts"]["1983-generated"]["season_dir"]).to_dict()
        if reference_rules.get("season") != 1983 or reference_rules != generated_rules:
            raise ValueError("Reference and generated source-year rules differ")
        result["rules_match"] = True
        result["partition_counts"] = {label: list(partitions.values()).count(label) for label in ("development", "withheld")}
        retrospective = any(entry["partition"] == "withheld" and entry["inspected_before_freeze"]
                            for entry in mappings.values())
        result["validation_class"] = ("retrospective-cross-validation" if retrospective
                                       else "declared-withheld-team-validation")
        result["unconsumed_files"] = sorted(set(declared) - {"1983.yaml", "ai_behavior.yaml"} - {
            f"{folder}/{name}" for folder in folders
            for name in ("offense.csv", "defense.csv", "special.csv", "team.yaml", "roster.json")})
        for name in sorted(mappings):
            entry = mappings[name]
            try:
                metadata = safe_load((directory / entry["reference_folder"] / "team.yaml").read_bytes())
                if (not isinstance(metadata, dict) or not isinstance(metadata.get("team_name"), str)
                        or not metadata["team_name"].strip()):
                    raise ValueError("Reference team metadata needs a readable, named mapping")
                decoded = chart_audit.audit_chart_decoder(directory / entry["reference_folder"])
                if (not isinstance(decoded, dict) or type(decoded.get("passed")) is not bool
                        or not isinstance(decoded.get("errors"), list)
                        or not isinstance(decoded.get("limitations"), list)
                        or not isinstance(decoded.get("loader_warnings"), list)):
                    raise ValueError("Malformed reference decoder result")
                if decoded["passed"] is not True or decoded["errors"]:
                    errors.extend([f"{name}: {reason}" for reason in decoded["errors"]]
                                  or [f"{name}: reference decoder failed"])
                teams[name] = {**entry, "metadata": metadata, "decoder": decoded}
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError, YAMLError) as error:
                errors.append(f"{name}: {error}")
                teams[name] = {**entry, "decoder": {"passed": False, "errors": [str(error)]}}
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError, YAMLError) as error:
        errors.append(str(error))
    if directory is not None and before is not None:
        try:
            _local_directory(root, corpus["directory"])
            if reference_corpus_inventory(directory) != before:
                errors.append("Reference corpus files or directories changed during validation")
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
            errors.append(f"Final reference census: {error}")
    result["passed"] = not errors
    return result


def _fraction_pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _probability(value: object) -> Fraction:
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(part) is not int for part in value)
            or value[0] < 0 or value[1] <= 0 or value[0] > value[1]):
        raise ValueError("Exact probability needs two integers with 0 <= numerator <= denominator")
    return Fraction(*value)


def _distribution(value: object) -> dict[str, Fraction]:
    if not isinstance(value, dict) or not value or any(not isinstance(key, str) or not key for key in value):
        raise ValueError("Exact distribution needs nonempty string keys")
    masses = {key: _probability(pair) for key, pair in value.items()}
    if sum(masses.values()) != 1:
        raise ValueError("Exact distribution does not conserve probability")
    return masses


def _validate_exact(report: dict[str, Any]) -> None:
    """Validate measured component evidence before computing any comparison."""
    expected = {f"{name}/{formation}" for name in chart_audit._OFFENSE_NAMES[:9] for formation in "ABCDEF"}
    if not isinstance(report, dict) or not isinstance(report.get("plays"), dict) or set(report["plays"]) != expected:
        raise ValueError("Exact report must cover all nine calls and six defenses")
    for call, play in report["plays"].items():
        marginal = _distribution(play["exact_masses"])
        joint = _distribution(play["exact_joint_masses"])
        summed: dict[str, Fraction] = {}
        for label, mass in joint.items():
            if not re.fullmatch(
                r"(?:(?:yards|breakaway|scramble|sack|incomplete|pending_fumble|pending_qt_fumble|pending_interception):-?\d+"
                r"|pending_penalty|pending_touchdown_distance)\|oob=[01]", label,
            ):
                raise ValueError(f"{call}: invalid joint outcome label")
            kind, flag = label.rsplit("|", 1)
            if (kind.startswith("pending_") or kind == "incomplete:0") and flag != "oob=0":
                raise ValueError(f"{call}: unresolved/incomplete outcome cannot assert an OOB flag")
            summed[kind] = summed.get(kind, Fraction()) + mass
        if summed != marginal or _probability(play["exact_total_mass"]) != 1:
            raise ValueError(f"{call}: joint outcome marginal/total does not reconcile")
        triggers = play["trigger_exact_masses"]
        if not isinstance(triggers, dict) or set(triggers) != {"qt", "breakaway"}:
            raise ValueError(f"{call}: incomplete secondary trigger evidence")
        trigger_mass = sum(_probability(pair) for pair in triggers.values())
        if trigger_mass > 1 or _probability(play["secondary_fallback_exact_mass"]) > trigger_mass:
            raise ValueError(f"{call}: invalid secondary trigger/fallback mass")
    special = report["special_teams"]
    if not isinstance(special, dict) or set(special) != {*chart_audit._SPECIAL_NAMES, "fumble_return"}:
        raise ValueError("Exact report must cover every special-teams lookup")
    for values in special.values():
        _distribution(values["exact_masses"])
    curve = special["field_goal"]["exact_by_distance"]
    if not isinstance(curve, dict) or set(curve) != {str(distance) for distance in range(18, 76)}:
        raise ValueError("Exact field-goal curve has missing or extra distances")
    probabilities = [_probability(curve[str(distance)]) for distance in range(18, 76)]
    if any(right > left for left, right in pairwise(probabilities)):
        raise ValueError("Field-goal coverage must not increase with distance")
    recovery = _distribution(report["exact_recovery"])
    if set(recovery) != {"retained", "lost"}:
        raise ValueError("Exact recovery evidence needs retained and lost outcomes")
    _probability(report["extra_point_exact_miss_mass"])


def _numeric_summary(play: dict[str, Any]) -> dict[str, Any]:
    masses = _distribution(play["exact_joint_masses"])
    known: list[tuple[int, Fraction]] = []
    pending = oob = Fraction()
    for label, mass in masses.items():
        kind, flag = label.rsplit("|", 1)
        if kind.startswith("pending_"):
            pending += mass
        if flag == "oob=1":
            oob += mass
        category, _, yards = kind.partition(":")
        if category in {"yards", "breakaway", "scramble", "sack"}:
            known.append((int(yards), mass))
    probability = sum((mass for _, mass in known), Fraction())
    moment = sum((yards * mass for yards, mass in known), Fraction())
    return {
        "probability": _fraction_pair(probability),
        "conditional_mean": _fraction_pair(moment / probability) if probability else None,
        "yard_moment_per_lookup": _fraction_pair(moment),
        "pending_probability": _fraction_pair(pending),
        "out_of_bounds_probability": _fraction_pair(oob),
        **{name: _fraction_pair(sum((mass for yards, mass in known if predicate(yards)), Fraction()))
           for name, predicate in (("loss_probability", lambda yards: yards < 0),
                                   ("zero_probability", lambda yards: yards == 0),
                                   ("tail_20_probability", lambda yards: yards >= 20),
                                   ("tail_40_probability", lambda yards: yards >= 40))},
    }


def _contrast(reference: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    before, after = _distribution(reference), _distribution(generated)
    delta = {key: after.get(key, Fraction()) - before.get(key, Fraction()) for key in sorted(before.keys() | after.keys())}
    delta = {key: mass for key, mass in delta.items() if mass}
    return {"delta": {key: _fraction_pair(mass) for key, mass in delta.items()},
            "total_variation": _fraction_pair(sum(map(abs, delta.values()), Fraction()) / 2)}


def _scalar_contrast(reference: object, generated: object) -> dict[str, Any]:
    before, after = _probability(reference), _probability(generated)
    return {"reference": _fraction_pair(before), "generated": _fraction_pair(after),
            "delta": _fraction_pair(after - before)}


def compare_reference_weighted(
    generated: Mapping[str, TeamChart], reference: Mapping[str, TeamChart],
) -> dict[str, Any]:
    """Compare complete matched cohorts using exact pre-state chart mechanics.

    R/R, G/R, R/G and G/G use the same uniform opposing-cohort mixture, including
    the named team's own defense. This exploratory conditioning is separate from
    source-schedule fit and stateful crossed games. Differences have no universal
    acceptance threshold and never establish historical or release accuracy.
    """
    errors: list[str] = []
    teams: dict[str, Any] = {}
    result: dict[str, Any] = {
        "passed": False, "errors": errors, "teams": teams, "ranking": [],
        "weighted_validated": False, "behavior_matches_reference": False,
        "stateful_crossed_complete": False, "benchmark_complete": False,
        "source_accepted": False, "ready_for_owner_review": False, "release_certified": False,
        "interpretation": "Exact pre-state uniform-cohort diagnostics; pending branches remain unresolved. "
                          "Agreement is not source accuracy, stateful game evidence or release acceptance.",
    }
    if (not isinstance(generated, Mapping) or not isinstance(reference, Mapping) or not generated
            or set(generated) != set(reference)
            or any(not isinstance(name, str) or not name for name in generated)
            or any(not isinstance(chart, TeamChart) for cohort in (generated, reference) for chart in cohort.values())):
        errors.append("Requires nonempty, complete, identically mapped TeamChart cohorts")
        return result
    names = sorted(generated)
    result["uniform_defense_team_count"] = len(names)
    opponents = {"r": [reference[name] for name in names], "g": [generated[name] for name in names]}
    for name in names:
        team_errors: list[str] = []
        details: dict[str, Any] = {"passed": False, "errors": team_errors, "scenarios": {}}
        teams[name] = details
        for scenario, offense in (("rr", reference[name]), ("gr", generated[name]),
                                  ("rg", reference[name]), ("gg", generated[name])):
            try:
                measured = chart_audit._exact_team_mechanics(offense, opponents[scenario[1]])
                _validate_exact(measured)
                measured["known_numeric"] = {call: _numeric_summary(play) for call, play in measured["plays"].items()}
                details["scenarios"][scenario] = measured
            except (ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError, OverflowError, RuntimeError) as error:
                team_errors.append(f"{scenario}: {error}")
        if team_errors:
            errors.extend(f"{name}: {error}" for error in team_errors)
            continue
        rr, gg = (details["scenarios"][scenario] for scenario in ("rr", "gg"))
        plays = {}
        for call in sorted(rr["plays"]):
            distributions = {scenario: measured["plays"][call]["exact_joint_masses"]
                             for scenario, measured in details["scenarios"].items()}
            crossed = {scenario: _distribution(distribution) for scenario, distribution in distributions.items()}
            keys = set().union(*(distribution.keys() for distribution in crossed.values()))
            interaction = {key: crossed["gg"].get(key, Fraction()) - crossed["gr"].get(key, Fraction())
                           - crossed["rg"].get(key, Fraction()) + crossed["rr"].get(key, Fraction()) for key in sorted(keys)}
            interaction = {key: mass for key, mass in interaction.items() if mass}
            plays[call] = {
                **{label: _contrast(distributions["rr"], distributions[scenario])
                   for label, scenario in (("offense", "gr"), ("defense", "rg"), ("joint", "gg"))},
                "interaction": {"delta": {key: _fraction_pair(mass) for key, mass in interaction.items()},
                                "l1": _fraction_pair(sum(map(abs, interaction.values()), Fraction()))},
                "triggers": {trigger: _scalar_contrast(rr["plays"][call]["trigger_exact_masses"][trigger],
                                                       gg["plays"][call]["trigger_exact_masses"][trigger])
                             for trigger in ("qt", "breakaway")},
                "secondary_fallback": _scalar_contrast(rr["plays"][call]["secondary_fallback_exact_mass"],
                                                       gg["plays"][call]["secondary_fallback_exact_mass"]),
            }
        details["plays"] = plays
        worst = min(plays, key=lambda call: (-Fraction(*plays[call]["joint"]["total_variation"]), call))
        details["worst_joint_call"] = worst
        details["max_joint_total_variation"] = plays[worst]["joint"]["total_variation"]
        details["special_teams"] = {
            column: _contrast(rr["special_teams"][column]["exact_masses"], gg["special_teams"][column]["exact_masses"])
            for column in sorted(rr["special_teams"])}
        details["field_goal_by_distance"] = {
            distance: _scalar_contrast(rr["special_teams"]["field_goal"]["exact_by_distance"][distance],
                                       gg["special_teams"]["field_goal"]["exact_by_distance"][distance])
            for distance in rr["special_teams"]["field_goal"]["exact_by_distance"]}
        details["recovery"] = _contrast(rr["exact_recovery"], gg["exact_recovery"])
        details["extra_point_miss"] = _scalar_contrast(rr["extra_point_exact_miss_mass"], gg["extra_point_exact_miss_mass"])
        details["passed"] = True
    result["ranking"] = sorted((name for name in names if teams[name]["passed"]),
                               key=lambda name: (-Fraction(*teams[name]["max_joint_total_variation"]), name))
    result["passed"] = result["weighted_validated"] = not errors
    result["behavior_matches_reference"] = not errors and all(
        all(all(not play[label]["delta"] for label in ("offense", "defense", "joint", "interaction"))
            and all(not Fraction(*values["delta"]) for values in play["triggers"].values())
            and not Fraction(*play["secondary_fallback"]["delta"]) for play in details["plays"].values())
        and all(not values["delta"] for values in details["special_teams"].values())
        and not details["recovery"]["delta"] and not Fraction(*details["extra_point_miss"]["delta"])
        and all(not Fraction(*values["delta"]) for values in details["field_goal_by_distance"].values())
        for details in teams.values())
    return result


def _load_matched_reference_charts(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any],
) -> tuple[dict[str, TeamChart], dict[str, TeamChart]]:
    """Load every mapped team after preflight; never compare a partial mixture."""
    generated: dict[str, TeamChart] = {}
    reference: dict[str, TeamChart] = {}
    errors: list[str] = []
    candidate = root / freeze["cohorts"]["1983-generated"]["season_dir"]
    corpus = root / evidence["corpus"]["directory"]
    for name, entry in sorted(evidence["corpus"]["teams"].items()):
        for label, directory, charts in (
            ("generated", candidate / name, generated),
            ("reference", corpus / entry["reference_folder"], reference),
        ):
            try:
                charts[name] = load_team_chart(str(directory))
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                errors.append(f"{name} {label}: {error}")
    if errors:
        raise ValueError("; ".join(errors))
    return generated, reference


def run_reference_context_trial(
    offense: TeamChart, defense: TeamChart, context: str, play: PlayType, formation: DefenseType, seed: int,
) -> dict[str, Any]:
    """Delegate one bounded trial to the authoritative-engine context collector."""
    from .chart_reference_context_audit import run_context_trial

    return run_context_trial(offense, defense, context, play, formation, seed)


def compare_reference_contexts(
    generated: Mapping[str, TeamChart], reference: Mapping[str, TeamChart],
) -> dict[str, Any]:
    """Collect all matched stateful contexts, leaving benchmark acceptance pending."""
    from .chart_reference_context_audit import collect_reference_contexts

    return collect_reference_contexts(generated, reference, run_reference_context_trial)


def compare_reference_campaigns(
    generated: dict[str, Any], original: dict[str, Any], contract: dict[str, Any],
    generated_dir: Path, reference_dir: Path, mapping: Mapping[str, str], *, master: int = 20461108,
) -> dict[str, Any]:
    """Compare complete raw campaigns through the shared engine evidence validator."""
    from .chart_reference_pair_audit import compare_campaigns

    return compare_campaigns(generated, original, contract, generated_dir, reference_dir, mapping, master=master)
