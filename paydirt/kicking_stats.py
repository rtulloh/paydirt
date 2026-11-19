"""Authoritative field-goal counter names and statistical distance bands."""
from typing import Any

FIELD_GOAL_BANDS = ("0_19", "20_29", "30_39", "40_49", "50_plus")
FIELD_GOAL_FIELDS = tuple(f"field_goals{suffix}_{kind}"
                          for suffix in ("", *("_" + band for band in FIELD_GOAL_BANDS))
                          for kind in ("attempted", "made"))


def empty_field_goal_stats() -> dict[str, int]:
    return dict.fromkeys(FIELD_GOAL_FIELDS, 0)


def validate_field_goal_stats(value: Any) -> dict[str, int] | None:
    """Validate optional historical coverage without filling absent counters."""
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - set(FIELD_GOAL_FIELDS):
        raise ValueError("Invalid field-goal statistics")
    for key, number in value.items():
        if type(number) is not int or not 0 <= number <= 1_000_000_000:
            raise ValueError("Invalid field-goal counter")
        if key.endswith("_made"):
            attempted = key.removesuffix("_made") + "_attempted"
            if attempted in value and number > value[attempted]:
                raise ValueError("Field goals made exceed attempts")
    for kind in ("made", "attempted"):
        total = f"field_goals_{kind}"
        bands = [f"field_goals_{band}_{kind}" for band in FIELD_GOAL_BANDS]
        if total in value:
            known = sum(value[key] for key in bands if key in value)
            if known > value[total] or all(key in value for key in bands) and known != value[total]:
                raise ValueError("Field-goal distance bands disagree with total")
    return dict(value)


def record_field_goal(stats: Any, distance: int, made: bool) -> None:
    """Record a retained kick; legacy games with unknown prior coverage stay unknown."""
    counters = stats._field_goal_stats
    if counters is None:
        return
    band = "0_19" if distance < 20 else "20_29" if distance < 30 else "30_39" if distance < 40 else "40_49" if distance < 50 else "50_plus"
    for prefix in ("field_goals", f"field_goals_{band}"):
        for kind, amount in (("attempted", 1), ("made", int(made))):
            key = f"{prefix}_{kind}"
            if key in counters:
                counters[key] += amount
