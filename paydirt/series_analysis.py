"""Exact, bounded continuation diagnostics; deliberately not an AI selector.

The caller supplies a reviewed full-state transition model. This module knows no
football rules, does not read charts or selected opponent calls, and never rolls
dice. It evaluates the supplied baseline policy under all supplied formations.
Unknown, cyclic, or budget-limited continuations retain their entire [0, 1]
probability range. A separate exact local certificate can reject unsafe proposals.

Model completeness and state identity are caller obligations: an incomplete
football adapter is not made correct by exact arithmetic. No gameplay path uses
this diagnostic API.
"""

from collections import Counter
from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from types import MappingProxyType


def _exact(value: object, label: str) -> Fraction:
    """Preserve the exact value supplied, including actual finite float weights."""
    if type(value) is float and isfinite(value):
        return Fraction.from_float(value)
    if type(value) is int or isinstance(value, Fraction):
        return Fraction(value)
    raise ValueError(f"{label} must be a finite rational number")


@dataclass(frozen=True)
class ProbabilityInterval:
    """Inclusive, exact bounds on the original offense's continuation success."""

    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        lower = _exact(self.lower, "Lower probability")
        upper = _exact(self.upper, "Upper probability")
        if not 0 <= lower <= upper <= 1:
            raise ValueError("Probability bounds must satisfy 0 <= lower <= upper <= 1")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)


UNKNOWN = ProbabilityInterval(Fraction(0), Fraction(1))


@dataclass(frozen=True)
class SeriesOutcome:
    """A terminal result, full-state successor, or explicitly unknown branch.

    Set success to True/False for a terminal. Set successor for continuation.
    Leave both unset for unknown. Never supply both. Probability is unconditional
    physical mass within this action/formation, not renormalized known mass.
    """

    probability: Fraction
    success: bool | None = None
    successor: Hashable | None = None


@dataclass(frozen=True)
class SeriesNode:
    """Baseline action weights and action -> formation -> physical branches."""

    prior: Mapping[str, Fraction]
    outcomes: Mapping[str, Mapping[str, tuple[SeriesOutcome, ...]]]


@dataclass(frozen=True)
class SeriesPreview:
    """Immutable diagnostics; unknown counts count evaluated branches, not mass."""

    baseline: ProbabilityInterval
    action_bounds: Mapping[str, ProbabilityInterval]
    expanded_nodes: int
    unknown_reasons: Mapping[str, int]


@dataclass(frozen=True)
class ProposalCertificate:
    """Local advantage under the supplied Q-baseline intervals, not release proof."""

    accepted: bool
    proposal_lower_advantage: Fraction
    returned_weights: Mapping[str, Fraction]
    total_variation: Fraction


def _weights(raw: Mapping[str, Fraction]) -> dict[str, Fraction]:
    if not isinstance(raw, Mapping) or not raw:
        raise ValueError("Action weights must be a nonempty mapping")
    weights = {action: _exact(weight, "Action weight") for action, weight in raw.items()}
    if any(not isinstance(action, str) or not action for action in weights):
        raise ValueError("Action weights require nonempty string action names")
    total = sum(weights.values(), Fraction())
    if any(weight < 0 for weight in weights.values()) or total <= 0:
        raise ValueError("Action weights must be nonnegative with a positive total")
    return {action: weight / total for action, weight in weights.items()}


def _state_key(state: Hashable) -> Hashable:
    try:
        hash(state)
    except TypeError as error:
        raise ValueError("Series state identity must be immutable and hashable") from error
    return state


def _validated_node(node: SeriesNode) -> tuple[dict, dict]:
    if not isinstance(node, SeriesNode):
        raise TypeError("Transition model must return a SeriesNode")
    prior = _weights(node.prior)
    if not isinstance(node.outcomes, Mapping) or set(prior) != set(node.outcomes):
        raise ValueError("Transition actions must exactly match baseline weight actions")
    outcomes = {}
    expected_formations = None
    for action, raw_forms in node.outcomes.items():
        if not isinstance(raw_forms, Mapping) or not raw_forms:
            raise ValueError("Every action requires nonempty formation coverage")
        forms = set(raw_forms)
        if any(not isinstance(form, str) or not form for form in forms):
            raise ValueError("Formation names must be nonempty strings")
        if expected_formations is None:
            expected_formations = forms
        elif forms != expected_formations:
            raise ValueError("Every action must cover the same complete formation set")
        outcomes[action] = {}
        for formation, raw_branches in raw_forms.items():
            branches = []
            for event in raw_branches:
                if not isinstance(event, SeriesOutcome):
                    raise TypeError("Physical branches must be SeriesOutcome values")
                mass = _exact(event.probability, "Physical probability")
                if not 0 <= mass <= 1:
                    raise ValueError("Physical probability must be between zero and one")
                if event.success is not None and type(event.success) is not bool:
                    raise ValueError("Terminal success must be True, False or unknown")
                if event.success is not None and event.successor is not None:
                    raise ValueError("A terminal outcome cannot also have a successor")
                if event.successor is not None:
                    _state_key(event.successor)
                branches.append((mass, event.success, event.successor))
            if sum((mass for mass, _, _ in branches), Fraction()) != 1:
                raise ValueError("Physical branch mass must sum exactly to one")
            outcomes[action][formation] = tuple(branches)
    return prior, outcomes


def evaluate_series(
    initial: Hashable,
    model: Callable[[Hashable], SeriesNode],
    *,
    max_nodes: int = 256,
    max_depth: int = 32,
) -> SeriesPreview:
    """Bound baseline continuation without guessing unknown or cyclic transitions.

    Args:
        initial: Complete immutable state identity, including relevant history,
            clock, phase and pending procedures; never just down and distance.
        model: Reviewed pure transition callback using public charts and earlier
            revealed history, never either current hidden call or future dice.
            Supply every possible formation
            and complete physical branch mass. Future nodes retain their baseline
            mixtures; this is not max-action recursion or a candidate future policy.
        max_nodes: Maximum distinct states expanded by this call.
        max_depth: Maximum recursive expansion depth, bounded to protect the stack.

    Returns:
        Exact action and baseline bounds. Formation minima/maxima permit arbitrary
        future formation choices; no selected or forecast formation is inspected.
        Resource bounds limit expansions, not the runtime of a caller's callback.
    """
    if type(max_nodes) is not int or max_nodes < 1:
        raise ValueError("max_nodes limit must be a positive integer")
    if type(max_depth) is not int or not 1 <= max_depth <= 64:
        raise ValueError("max_depth limit must be an integer between one and 64")
    _state_key(initial)
    cache = {}
    active = set()
    unknown = Counter()
    expanded = 0
    root_actions = {}

    def visit(state: Hashable, depth: int) -> ProbabilityInterval:
        nonlocal expanded, root_actions
        if state in active:
            unknown["cycle"] += 1
            return UNKNOWN
        if state in cache:
            return cache[state]
        if depth >= max_depth:
            unknown["depth_limit"] += 1
            return UNKNOWN
        if expanded >= max_nodes:
            unknown["node_limit"] += 1
            return UNKNOWN
        prior, outcomes = _validated_node(model(state))
        expanded += 1
        active.add(state)
        action_bounds = {}
        for action, forms in outcomes.items():
            formation_bounds = []
            for branches in forms.values():
                lower = upper = Fraction()
                for mass, terminal, successor in branches:
                    if not mass:
                        continue
                    if terminal is not None:
                        bound = ProbabilityInterval(Fraction(int(terminal)), Fraction(int(terminal)))
                    elif successor is None:
                        unknown["explicit"] += 1
                        bound = UNKNOWN
                    else:
                        bound = visit(successor, depth + 1)
                    lower += mass * bound.lower
                    upper += mass * bound.upper
                formation_bounds.append(ProbabilityInterval(lower, upper))
            action_bounds[action] = ProbabilityInterval(
                min(bound.lower for bound in formation_bounds),
                max(bound.upper for bound in formation_bounds),
            )
        value = ProbabilityInterval(
            sum((prior[action] * bound.lower for action, bound in action_bounds.items()), Fraction()),
            sum((prior[action] * bound.upper for action, bound in action_bounds.items()), Fraction()),
        )
        active.remove(state)
        cache[state] = value
        if depth == 0:
            root_actions = action_bounds
        return value

    baseline = visit(initial, 0)
    return SeriesPreview(baseline, MappingProxyType(root_actions), expanded,
                         MappingProxyType(dict(unknown)))


def certify_proposal(
    prior: Mapping[str, Fraction],
    proposed: Mapping[str, Fraction],
    action_bounds: Mapping[str, ProbabilityInterval],
) -> ProposalCertificate:
    """Return a proposal only if its worst local Q-baseline advantage is >= zero.

    The supplied baseline and proposal must share action names and the proposal
    cannot add positive support. Unknown intervals never become neutral point
    estimates. This is a local algebraic certificate, not proof of properness,
    football model validity, whole-policy gain, historical fidelity or fairness.
    """
    baseline = _weights(prior)
    proposal = _weights(proposed)
    if set(baseline) != set(proposal) or set(baseline) != set(action_bounds):
        raise ValueError("Baseline, proposal and bounds must have identical action sets")
    if any(proposal[action] and not baseline[action] for action in baseline):
        raise ValueError("Proposal cannot add positive action support")
    advantage = Fraction()
    for action, before in baseline.items():
        bound = action_bounds[action]
        if not isinstance(bound, ProbabilityInterval):
            raise TypeError("Action bounds must be ProbabilityInterval values")
        difference = proposal[action] - before
        advantage += difference * (bound.lower if difference >= 0 else bound.upper)
    accepted = advantage >= 0
    returned = proposal if accepted else baseline
    variation = sum((abs(returned[action] - baseline[action]) for action in baseline), Fraction()) / 2
    return ProposalCertificate(accepted, advantage, MappingProxyType(returned), variation)
