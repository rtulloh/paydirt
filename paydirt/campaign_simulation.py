"""Run one campaign fixture with the existing CPU game orchestration."""
from __future__ import annotations

import contextlib
import io
import random
from pathlib import Path

from .auto_game import run_auto_game
from .computer_ai import create_computer_ai
from .game_engine import PaydirtGameEngine


class _DiscardNarrative(io.TextIOBase):
    """Discard chart narrative instead of retaining it in a browser or public receipt."""

    def write(self, text: str) -> int:
        return len(text)


def simulate_game(
    home_path: Path | str, away_path: Path | str, rules_dir: Path | str, *,
    is_playoff: bool = False, seed: int | None = None, play_limit: int = 750,
) -> PaydirtGameEngine:
    """Simulate one fixture under fixed rules without advancing the caller RNG.

    The caller resolves catalog identities and owns result persistence. A failed
    or unfinished simulation raises; it never supplies a provisional final score.
    Calls are synchronous and must be serialized with other engine mutations by
    the hosting runtime (the browser bridge already serializes operations).
    """
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError('Simulation seed must be a nonnegative integer')
    previous_random_state = random.getstate()
    try:
        # Seeding from system entropy when not specified avoids repeating a
        # fixture merely because the caller stream is deliberately preserved.
        random.seed(seed)
        with contextlib.redirect_stdout(_DiscardNarrative()):
            game = run_auto_game(
                str(away_path), str(home_path), is_playoff=is_playoff,
                rules_dir=Path(rules_dir), display_stats=False, play_limit=play_limit,
                ai_factory=lambda engine, home: create_computer_ai('hard', engine, cpu_is_home=home),
            )
        if (game is None or not game.state.game_over or game.has_untimed_down()
                or game.pending_post_score_action() is not None
                or game.has_pending_end_zone_interception
                or is_playoff and game.state.home_score == game.state.away_score):
            raise RuntimeError('Simulation did not produce a legal final game')
        return game
    finally:
        random.setstate(previous_random_state)
