"""Test-server-only diagnostics; never included in production bundles."""
import json
import random
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any


def instrument_simulation(original: Callable[..., Any]) -> Callable[..., Any]:
    """Observe the already-seeded real call without retrying or changing its result."""
    @wraps(original)
    def observed(*args: Any, **kwargs: Any) -> Any:
        rng_state = random.getstate()
        game = original(*args, **kwargs)
        flags = {"missing_engine": game is None}
        if game is not None:
            flags.update(game_over=game.state.game_over, untimed_down=game.has_untimed_down(),
                         post_score_action=game.pending_post_score_action(),
                         end_zone_choice=game.has_pending_end_zone_interception,
                         tied_playoff=bool(kwargs.get("is_playoff") and game.state.home_score == game.state.away_score))
        if (game is None or not flags["game_over"] or flags["untimed_down"]
                or flags["post_score_action"] is not None or flags["end_zone_choice"] or flags["tied_playoff"]):
            print(json.dumps({"kind": "e2e-campaign-final-diagnostic", "rng_state": rng_state,
                              "flags": flags}), file=sys.stderr, flush=True)
        return game
    return observed
