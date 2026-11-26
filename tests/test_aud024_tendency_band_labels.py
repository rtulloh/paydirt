"""AUD-024: postgame tendency rows must label their aggregation bands."""

from paydirt.ai_analysis import OpponentTendencyTracker
from paydirt import interactive_game


def tracker() -> OpponentTendencyTracker:
    tracker = OpponentTendencyTracker()
    tracker.record_play(3, 4, "short_pass", 5)
    tracker.record_play(3, 6, "short_pass", 5)
    tracker.record_play(2, 7, "off_tackle", 5)
    tracker.record_play(4, 2, "line_plunge", 5)
    tracker.record_play(1, 4, "screen", 5)
    return tracker


def test_displayed_labels_name_the_actual_aggregation_band() -> None:
    rows = dict(interactive_game._tendency_summary_rows(tracker()))
    assert rows["1st down (any distance)"].total_plays == 1
    assert rows["2nd & 7+"].total_plays == 1
    assert rows["3rd & 4-6"].total_plays == 2
    assert rows["4th & 1-3"].total_plays == 1


def test_exact_distance_exemplars_are_not_printed_as_exact_situations() -> None:
    labels = " ".join(label for label, _ in interactive_game._tendency_summary_rows(tracker()))
    assert "1st & 10" not in labels
    assert "3rd & 5" not in labels
    assert "4th & 3" not in labels
