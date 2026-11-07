"""Shared pass-family inference and disclosed modeled interception locations.

Catch depth is air distance. Completion net gains can include yards after catch
and must not use these inference boundaries. Explicit source call labels take
precedence over inference; modeled locations are fallbacks, not hard spot caps.
"""

from collections.abc import Mapping
from types import MappingProxyType

MODELED_INTERCEPTION_DEPTHS: Mapping[str, int] = MappingProxyType({
    "screen": 5,
    "short_pass": 5,
    "medium_pass": 12,
    "long_pass": 20,
    "te_short_long": 8,
})


def pass_chart_for_air_depth(depth: float) -> str:
    """Infer a pass family using the structured source adapter's air-depth bins."""
    if depth <= 0:
        return "screen"
    if depth <= 9:
        return "short_pass"
    if depth <= 19:
        return "medium_pass"
    return "long_pass"
