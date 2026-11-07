"""Exact chart-resolution controls for generated-defense release validation.

These controls measure tactical contrast, not historical accuracy. Penalty choices
and fumble recoveries remain explicit pending branches rather than zero-yard plays.
The resolver's RNG entry points are patched within a scoped, single-threaded audit.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from fractions import Fraction
from unittest.mock import patch

from . import play_resolver as resolver
from .chart_generator import EmpiricalPassCalibration
from .chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from .play_resolver import CHART_PLAY_TYPES, DefenseType, PlayType
from .priority_chart import apply_priority_chart


@dataclass(frozen=True)
class ResolvedOutcome:
    """Observable resolver outcome; unresolved gain has no numeric yard value."""

    kind: str
    yards: int | None
    turnover: bool | None = False
    touchdown: bool = False
    pending: bool = False
    detail: str = ""


@dataclass(frozen=True)
class TacticalFinding:
    code: str
    message: str
    contract: str = ""


@dataclass
class TacticalAuditResult:
    findings: list[TacticalFinding] = field(default_factory=list)
    contrasts: dict[str, int] = field(default_factory=dict)
    contracts: dict[str, dict[str, str]] = field(default_factory=dict)
    diagnostics: list[TacticalFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings


def controlled_offense(token: str = "10") -> TeamChart:
    """Create synthetic identical play columns with complete secondary tables."""
    offense = OffenseChart(
        **{play.value: dict.fromkeys(range(10, 40), token) for play in CHART_PLAY_TYPES},
        breakaway=dict.fromkeys(range(10, 40), "25"),
        qb_time=dict.fromkeys(range(10, 40), "-6"),
    )
    peripheral = PeripheralData(
        2026,
        "Synthetic",
        "Control",
        0,
        short_name="SYN",
        fumble_recovered_range=(10, 39),
    )
    return TeamChart(peripheral, offense, DefenseChart(), SpecialTeamsChart())


def _group_rows(column: dict[int, str]) -> list[tuple[int, int]]:
    groups: dict[str, tuple[int, int]] = {}
    for row, weight in resolver.chart_roll_weights().items():
        if row not in column:
            raise ValueError(f"Audit requires a complete chart; missing row {row}")
        raw = column[row]
        representative, mass = groups.get(raw, (row, 0))
        groups[raw] = representative, mass + weight
    return list(groups.values())


def resolved_outcome_distribution(
    offense: TeamChart,
    defense: DefenseChart,
    play: PlayType,
    formation: DefenseType,
) -> dict[ResolvedOutcome, Fraction]:
    """Enumerate real priority/B/QT resolution with the game's exact dice weights.

    This is a pre-state distribution. TD yardage, interception returns, penalty
    decisions and fumble recovery are not assigned invented net gains. The same
    resolver called by the engine handles all determined primary/secondary paths.
    """
    distribution: defaultdict[ResolvedOutcome, Fraction] = defaultdict(Fraction)
    defender = replace(offense, defense=defense)
    column = getattr(offense.offense, play.value)
    physical_rows = {1: (1, 0, 1), 2: (2, 0, 2), 3: (3, 0, 3), 4: (2, 2, 4), 5: (3, 2, 5)}
    for subrow, defense_weight in resolver.defense_subrow_weights().items():
        modifier = defense.modifiers.get((formation.value, subrow), {}).get(
            resolver._play_type_to_column(play)
        )
        if modifier is None:
            raise ValueError(f"Missing defensive cell {formation.value}{subrow}/{play.value}")
        for primary_row, offense_weight in _group_rows(column):
            raw = column[primary_row]
            mass = Fraction(defense_weight * offense_weight, 36 * 216)
            if resolver._is_penalty_result(raw)[0] or resolver._is_penalty_result(modifier)[0]:
                distribution[
                    ResolvedOutcome("pending_penalty", None, None, pending=True, detail=raw)
                ] += mass
                continue
            combined = apply_priority_chart(
                raw, modifier, is_passing_play=resolver.is_passing_play(play)
            )
            if combined.is_turnover and "INT" not in raw and "INT" not in modifier:
                distribution[
                    ResolvedOutcome("pending_fumble", None, None, pending=True, detail=raw)
                ] += mass
                continue
            secondary = (
                offense.offense.qb_time
                if combined.use_qt_column
                else offense.offense.breakaway
                if combined.use_breakaway
                else None
            )
            branches = _group_rows(secondary) if secondary is not None else [(primary_row, 216)]
            for secondary_row, secondary_weight in branches:
                if (
                    secondary is not None
                    and (resolver._parse_qb_time_value(secondary[secondary_row]) if combined.use_qt_column
                         else resolver._parse_column_value(secondary[secondary_row])) is None
                ):
                    raise ValueError(f"Unsupported secondary result {secondary[secondary_row]!r}")
                rolls = iter(((primary_row, "audit primary"), (secondary_row, "audit secondary")))
                with (
                    patch.object(resolver, "roll_chart_dice", lambda rolls=rolls: next(rolls)),
                    patch.object(
                        resolver, "roll_defense_dice", lambda subrow=subrow: physical_rows[subrow]
                    ),
                ):
                    choice = resolver.resolve_play_with_penalties(
                        offense, defender, play, formation
                    )
                result = choice.play_result
                if result.result_type == resolver.ResultType.FUMBLE:
                    outcome = ResolvedOutcome(
                        "pending_fumble", None, None, pending=True, detail="secondary"
                    )
                elif result.result_type == resolver.ResultType.INTERCEPTION:
                    outcome = ResolvedOutcome(
                        "interception", None, True, detail=f"depth:{result.yards}"
                    )
                elif result.touchdown:
                    outcome = ResolvedOutcome("touchdown", None, False, touchdown=True)
                else:
                    outcome = ResolvedOutcome(
                        result.result_type.value, result.yards, result.turnover, result.touchdown,
                        detail="retained_fumble_incompletion" if result.retained_fumble_incompletion else "",
                    )
                distribution[outcome] += mass * Fraction(secondary_weight, 216)
    if sum(distribution.values()) != 1:
        raise ValueError("Audit probability mass does not reconcile")
    return dict(distribution)


def audit_defense_tactics(defense: DefenseChart) -> TacticalAuditResult:
    """Measure explicit synthetic contracts, not empirical tactical accuracy.

    All 4/10/18-yard controls require nonidentical formation distributions. The
    benefit/cost benchmark sweeps all three controls. Spread/Screen is an
    exploratory direction because the player guide promises only spread coverage;
    its violations are reported separately rather than invented as a guarantee.
    """
    result = TacticalAuditResult()
    contracts = (
        ("short_yardage_line_benefit", DefenseType.SHORT_YARDAGE, PlayType.LINE_PLUNGE, -1),
        ("short_yardage_draw_cost", DefenseType.SHORT_YARDAGE, PlayType.DRAW, 1),
        ("spread_screen_benefit", DefenseType.SPREAD, PlayType.SCREEN, -1),
        ("spread_line_cost", DefenseType.SPREAD, PlayType.LINE_PLUNGE, 1),
        ("short_pass_short_benefit", DefenseType.SHORT_PASS, PlayType.SHORT_PASS, -1),
        ("short_pass_long_cost", DefenseType.SHORT_PASS, PlayType.LONG_PASS, 1),
        ("long_pass_long_benefit", DefenseType.LONG_PASS, PlayType.LONG_PASS, -1),
        ("long_pass_line_cost", DefenseType.LONG_PASS, PlayType.LINE_PLUNGE, 1),
        ("blitz_medium_benefit", DefenseType.BLITZ, PlayType.MEDIUM_PASS, -1),
        ("blitz_draw_cost", DefenseType.BLITZ, PlayType.DRAW, 1),
    )
    for token in ("4", "10", "18"):
        resolved = {}
        offense = controlled_offense(token)
        for play in CHART_PLAY_TYPES:
            distributions = [
                resolved_outcome_distribution(offense, defense, play, formation)
                for formation in DefenseType
            ]
            signatures = {frozenset(distribution.items()) for distribution in distributions}
            key = f"{token}:{play.value}"
            result.contrasts[key] = len(signatures)
            resolved[play] = dict(zip(DefenseType, distributions))
            if len(signatures) < 2:
                result.findings.append(
                    TacticalFinding(
                        "formation_contrast",
                        f"{key}: all six formations have identical weighted outcomes",
                    )
                )
        for name, formation, play, direction in contracts:
            baseline = _known_gain_mean(resolved[play][DefenseType.STANDARD])
            specialized = _known_gain_mean(resolved[play][formation])
            result.contracts[f"{token}:{name}"] = {
                "standard": str(baseline),
                "specialized": str(specialized),
            }
            if baseline is None or specialized is None or (specialized - baseline) * direction <= 0:
                target = result.findings if name != "spread_screen_benefit" else result.diagnostics
                target.append(
                    TacticalFinding(
                        "tactical_tradeoff",
                        f"{token}:{name}: expected {'higher' if direction > 0 else 'lower'} "
                        f"conditional known gain than Standard; got {specialized} versus {baseline}",
                        contract=name,
                    )
                )
    return result


def _known_gain_mean(distribution: dict[ResolvedOutcome, Fraction]) -> Fraction | None:
    """Conditional mean over known nonturnover gains, retaining incompletions.

    Unknown recovery/penalty/TD/INT branches are excluded from numerator AND
    denominator. This is not unconditional expected yards per play.
    """
    known = [
        (outcome.yards, mass)
        for outcome, mass in distribution.items()
        if outcome.yards is not None
        and not outcome.pending
        and not outcome.turnover
        and not outcome.touchdown
    ]
    total = sum((mass for _, mass in known), Fraction())
    if not total:
        return None
    return sum((yards * mass for yards, mass in known), Fraction()) / total


def audit_engine_controls(defense: DefenseChart) -> TacticalAuditResult:
    """Check controlled distributions through the real stateful engine.

    Own40, first-and10, ordinary opening-quarter clock, 100% yardage factors,
    complete constant B/QT and zero-yard return tables make the scored result
    deterministic conditional on the five defensive subrows. These are exactly
    weighted controls, not sampled whole-game or end-zone/late-game coverage.
    """
    from .game_engine import PaydirtGameEngine

    report = TacticalAuditResult()
    faces = {1: (1, 0, 1), 2: (2, 0, 2), 3: (3, 0, 3), 4: (2, 2, 4), 5: (3, 2, 5)}
    for token in ("4", "10", "18", "B", "QT", "(7)"):
        offense = controlled_offense(token)
        offense.peripheral.base_yardage_factor = 100
        offense.peripheral.reduced_yardage_factor = 100
        offense.special_teams.interception_return = dict.fromkeys(range(10, 40), "0")
        offense.special_teams.fumble_return = dict.fromkeys(range(10, 40), "0")
        defender = replace(
            offense, defense=defense, peripheral=replace(offense.peripheral, short_name="DEF")
        )
        for play in CHART_PLAY_TYPES:
            for formation in DefenseType:
                expected = resolved_outcome_distribution(offense, defense, play, formation)
                actual: defaultdict[ResolvedOutcome, Fraction] = defaultdict(Fraction)
                for subrow, weight in resolver.defense_subrow_weights().items():
                    engine = PaydirtGameEngine(offense, defender)
                    engine.state.is_home_possession = True
                    engine.state.ball_position = 40
                    engine.state.down = 1
                    engine.state.yards_to_go = 10
                    with (
                        patch.object(resolver, "roll_chart_dice", lambda: (10, "engine control")),
                        patch.object(
                            resolver, "roll_defense_dice", lambda subrow=subrow: faces[subrow]
                        ),
                    ):
                        outcome = engine.run_play_with_penalty_procedure(play, formation)
                    result = outcome.result
                    if outcome.pending_penalty_decision:
                        observed = ResolvedOutcome("pending_penalty", None, None, pending=True)
                    elif result.result_type == resolver.ResultType.INTERCEPTION:
                        observed = ResolvedOutcome(
                            "interception", None, outcome.turnover, detail=f"depth:{result.yards}"
                        )
                    elif outcome.touchdown:
                        observed = ResolvedOutcome(
                            "touchdown", None, outcome.turnover, touchdown=True
                        )
                    else:
                        observed = ResolvedOutcome(
                            result.result_type.value,
                            outcome.yards_gained,
                            outcome.turnover,
                            outcome.touchdown,
                        )
                    actual[observed] += Fraction(weight, 36)
                if dict(actual) != expected:
                    report.findings.append(
                        TacticalFinding(
                            "engine_resolution",
                            f"{token}:{play.value}:{formation.value}: stateful engine differs "
                            "from exact priority/supplemental control at own40",
                        )
                    )
    return report


def audit_priority_resolution() -> TacticalAuditResult:
    """Reject selected fumbles displaced by a lower-priority interception cell.

    Both resolver entry points must honor the same core priority decision. This
    isolates classification; stateful recovery/return correctness is separate.
    """
    report = TacticalAuditResult()
    for token in ("F", "F + 2", "F - 2"):
        offense = controlled_offense(token)
        defender = replace(
            offense,
            defense=DefenseChart(
                {("A", row): dict.fromkeys(range(1, 10), "INT 5") for row in range(1, 6)}
            ),
        )
        for route in (resolver.resolve_play, resolver.resolve_play_with_penalties):
            with (
                patch.object(resolver, "roll_chart_dice", lambda: (10, "priority control")),
                patch.object(resolver, "roll_defense_dice", lambda: (1, 0, 1)),
            ):
                output = route(offense, defender, PlayType.SHORT_PASS, DefenseType.STANDARD)
            actual = output.play_result if hasattr(output, "play_result") else output
            if actual.result_type != resolver.ResultType.FUMBLE:
                report.findings.append(
                    TacticalFinding(
                        "priority_resolution",
                        f"{route.__name__}: offense {token!r} versus defense INT5 selects fumble "
                        f"priority but is classified {actual.result_type.value!r}",
                        contract="fumble_over_interception",
                    )
                )
    from .game_engine import PaydirtGameEngine

    for token in ("F", "F + 2", "F - 2"):
        offense = controlled_offense(token)
        offense.special_teams.interception_return = dict.fromkeys(range(10, 40), "0")
        offense.special_teams.fumble_return = dict.fromkeys(range(10, 40), "0")
        defender = replace(
            offense,
            defense=DefenseChart(
                {("A", row): dict.fromkeys(range(1, 10), "INT 5") for row in range(1, 6)}
            ),
        )
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position = 40
        with (
            patch.object(resolver, "roll_chart_dice", lambda: (10, "priority engine")),
            patch.object(resolver, "roll_defense_dice", lambda: (1, 0, 1)),
        ):
            output = engine.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD
            )
        if output.result.result_type != resolver.ResultType.FUMBLE or output.turnover:
            report.findings.append(
                TacticalFinding(
                    "priority_resolution",
                    f"stateful engine: {token!r} versus INT5 must remain a recovered fumble; "
                    f"got {output.result.result_type.value!r}, turnover={output.turnover}",
                    contract="fumble_over_interception",
                )
            )
    return report


def audit_strength_order(stronger: DefenseChart, weaker: DefenseChart) -> TacticalAuditResult:
    """Check conditional known-gain ordering for an explicitly ordered pair.

    The caller declares the ordering from controlled source inputs. This does not
    infer a total ranking from unrelated real teams' mixed strengths. Turnovers
    and TDs remain separate outcomes, not invented zero-yard samples.
    """
    report = TacticalAuditResult()
    improved = tied = 0
    for token in ("4", "10", "18"):
        offense = controlled_offense(token)
        for play in CHART_PLAY_TYPES:
            for formation in DefenseType:
                strong = _known_gain_mean(
                    resolved_outcome_distribution(offense, stronger, play, formation)
                )
                weak = _known_gain_mean(
                    resolved_outcome_distribution(offense, weaker, play, formation)
                )
                if strong is None or weak is None or strong > weak:
                    report.findings.append(
                        TacticalFinding(
                            "strength_order",
                            f"{token}:{play.value}:{formation.value}: "
                            f"declared stronger defense allows {strong} versus {weak} conditional known gain",
                        )
                    )
                elif strong < weak:
                    improved += 1
                else:
                    tied += 1
    report.contrasts = {"strict_improvements": improved, "ties": tied}
    if improved == 0:
        report.findings.append(
            TacticalFinding(
                "strength_order",
                "Declared stronger defense has no observed known-gain improvement",
            )
        )
    return report


def audit_generated_strength_order() -> TacticalAuditResult:
    """Reject erased or inverted team-strength transformations in the generator.

    Synthetic rushing/passing efficiency varies independently while disruption
    rates stay fixed. Three combined profiles also run through the real engine.
    No local season data or empirical historical ranking is involved.
    """
    from . import chart_generator

    rates = {
        "strong": (3.3, 5.5),
        "neutral": (4.1, 7.2),
        "weak": (5.0, 8.5),
        "run_strong": (3.3, 7.2),
        "run_weak": (5.0, 7.2),
        "pass_strong": (4.1, 5.5),
        "pass_weak": (4.1, 8.5),
    }
    profiles = {}
    for name, (rush_average, pass_average) in rates.items():
        stats = chart_generator.TeamSeasonStats.from_dict(
            {
                "season": 2026,
                "team_name": f"Synthetic {name}",
                "defense": {
                    "rushing": {"attempts": 1000, "yards": round(rush_average * 1000)},
                    "passing": {
                        "attempts": 1000,
                        "yards": round(pass_average * 1000),
                        "interceptions": 25,
                        "sacks": 65,
                    },
                },
            }
        )
        profiles[name] = DefenseChart(chart_generator._generate_defense(stats))
    report = TacticalAuditResult()
    for stronger, weaker in (
        ("strong", "neutral"),
        ("neutral", "weak"),
        ("strong", "weak"),
        ("run_strong", "run_weak"),
        ("pass_strong", "pass_weak"),
    ):
        pair = audit_strength_order(profiles[stronger], profiles[weaker])
        label = f"{stronger}/{weaker}"
        report.findings.extend(
            TacticalFinding(f.code, f"{label}: {f.message}", f.contract) for f in pair.findings
        )
        report.contrasts.update({f"{label}:{key}": value for key, value in pair.contrasts.items()})
    if report.findings:
        return report
    for name in ("strong", "neutral", "weak"):
        engine = audit_engine_controls(profiles[name])
        report.findings.extend(
            TacticalFinding(f.code, f"{name}: {f.message}", f.contract) for f in engine.findings
        )
    return report


def audit_generated_offense_risk_order(
    calibration: EmpiricalPassCalibration | None = None,
) -> TacticalAuditResult:
    """Hold defenses fixed while varying only synthetic QB interception risk.

    Exact probabilities are per selected primary call, not official per-attempt
    rates. Stateful fitting uses the separately reconciled attempt denominator.
    The proposed calibration must not clamp all QB risk to the same value.
    """
    from . import chart_generator as generator

    calibration = calibration or generator.EmpiricalPassCalibration()
    profiles = {}
    for label, interceptions in (("low", 5), ("neutral", 25), ("high", 60)):
        stats = generator.TeamSeasonStats.from_dict({
            "season": 2026, "team_name": "Synthetic risk control",
            "offense": {"passing": {"attempts": 1000, "completions": 650,
                                     "yards": 7000, "interceptions": interceptions,
                                     "sacks": 65, "sack_yards": 390}},
            "defense": {"passing": {"attempts": 1000, "yards": 7200,
                                     "interceptions": 25, "sacks": 65},
                        "rushing": {"attempts": 1000, "yards": 4100}},
        })
        baseline = generator._generate_offense(stats, 8306)
        for play in CHART_PLAY_TYPES:
            if resolver.is_passing_play(play):
                calibrated = generator._calibrate_empirical_pass_events(
                    ("10",) * 1000, baseline[play.value], calibration,
                )
                baseline[play.value] = generator._empirical_column(calibrated, 8306)
        profiles[label] = replace(controlled_offense(), offense=OffenseChart(**baseline))
        defense = DefenseChart(generator._generate_defense(stats))
    report = TacticalAuditResult()
    for play in CHART_PLAY_TYPES:
        if not resolver.is_passing_play(play):
            continue
        for formation in DefenseType:
            probabilities = {}
            for label, chart in profiles.items():
                distribution = resolved_outcome_distribution(chart, defense, play, formation)
                probabilities[label] = sum(mass for outcome, mass in distribution.items()
                                           if outcome.kind == "interception")
            key = f"{play.value}/{formation.value}"
            report.contracts[key] = {
                label: str(float(probability)) for label, probability in probabilities.items()
            }
            report.contracts[key]["denominator"] = "selected primary calls; joint pre-state probability"
            column = resolver._play_type_to_column(play)
            protected = all(defense.modifiers[(formation.value, row)][column].startswith("(")
                            for row in resolver.defense_subrow_weights())
            report.contracts[key]["protected_override"] = str(protected).lower()
            if protected and len(set(probabilities.values())) == 1:
                continue  # Explicit complete override, not erased QB calibration.
            if not probabilities["low"] < probabilities["neutral"] < probabilities["high"]:
                report.findings.append(TacticalFinding(
                    "erased-offense-interception-strength",
                    f"{key}: synthetic interception risk is not strictly low < neutral < high",
                ))
    return report
