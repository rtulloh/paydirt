# Play-testing dice-weighted AI analysis

Current follow-ups and completed AI changes are indexed in the [issue tracker](issue-tracker.md#ai-work-and-evaluation).

## What changed

Offensive chart averages and positive-yardage rates now use the actual dice
probabilities instead of treating all 30 chart rows as equally likely. For
example, row 15 is six times as likely as row 10. The implemented white dice
are 0–5; sums of 9 and 10 both use row x9.

The dice algorithm, game rules, difficulty presets, and analysis usage rate are
unchanged. Hard still mixes chart suggestions with its existing situational
choices; this does not make it an always-optimizing opponent.

These remain **conditional chart metrics**, excluding penalties, interceptions,
fumbles, and breakaway results. BLACK remains an included zero-yard failure.
They do not measure full play value against a particular defense, conversion
probability, or turnover risk.

## Start with the AI on the weaker team

Run from the repository root. You control `--home`; the AI controls `--away`.
These examples require the named teams to be installed locally. No private
team charts or historical data are supplied by this document.

### Houston at Washington

```bash
python3 -m paydirt --play -d hard --home 1983/Redskins --away 1983/Oilers
```

### Kansas City at San Francisco

```bash
python3 -m paydirt --play -d hard --home 1983/49ers --away 1983/Chiefs
```

### Tampa Bay at Los Angeles

```bash
python3 -m paydirt --play -d hard --home 1983/Raiders --away 1983/Buccaneers
```

Keep difficulty on Hard for this experiment. Normal `--auto` games still use
balanced AI and do **not** exercise Hard chart analysis, even with `-d hard`.

## What to watch

For each game, note the matchup, final score, and a few specific decisions:

- Does the weaker AI use its team's strengths rather than repeat generic calls?
- Are its calls varied enough to make defensive choices interesting?
- Does it make plausible choices on short and long yardage?
- Can you identify a questionable decision *before* seeing the dice outcome?
- Does a loss feel like weaker personnel/bad rolls, or avoidable coaching?

Keep surprising decisions separate from unlucky results. A sensible call can
fail, and a poor call can succeed. The weighting change only affects chart
suggestions; it does not redesign goal-line, clock, or fourth-down strategy.

A few human games are useful feedback, not a reliable win-rate estimate. The
automated exploratory comparison used a Medium CPU as the stronger-side
surrogate, not a human, so its results cannot predict your personal difficulty.
