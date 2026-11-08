# 1977 season source feasibility

Recorded 2026-11-08 for the proposed v1.10.3 season addition. This is a
source-access checkpoint, not an implemented season or a release qualification.

The [Sports Reference announcement](https://www.sports-reference.com/blog/2026/08/1977-play-by-play-and-associated-stats-added-to-pro-football-reference/)
confirms that PFR added 1977 play-by-play on August 12, 2026. Its indexed primary
article explicitly identifies partial-game gaps: the final 1:30 of Washington at
Atlanta in Week 2, and the final 3:55 of the second quarter plus part of the fourth
quarter of St. Louis at Washington in Week 13. It also reports 185 fumbles with
unknown forced-fumble credit. That latter count concerns forced-fumble attribution;
it does not establish the number of unsupported generator gain/class/ownership
facts. Play-by-play is unofficial and can differ from corrected box-score totals.
The announcement therefore cannot establish complete source coverage.

## Bounded acquisition result

No 1977 raw-source cache or season template was found in the repository, its
ignored audit storage, the work tree or temporary storage. Direct public HTTP
requests for the 1977 schedule, a representative box score and Dallas team page
returned HTTP 403. Web retrieval of the schedule also returned 403. The existing
1983 set cites archived PFR HTML, but bounded Wayback CDX queries for the 1977
schedule in 2026 and the representative box score returned empty inventories;
a dated representative replay returned 404. These sampled checks do not prove
that no archive of any 1977 game exists. They do establish that the tested route
did not supply a usable input inventory.

The [official nflreadr loader](https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R)
requires seasons beginning in 1999. Its standard nflverse play-by-play feed cannot
supply 1977. No alternate complete, adapter-compatible public input was verified
in this bounded check. Search snippets are evidence about coverage, not raw
per-play inputs suitable for source hashing and generation.

## Decision and next dependency

Stop before generation. Reuse of `generate_pfr_charts.py` is plausible, but it
requires actual archived HTML, normalized team aggregates, a source-team map,
and a reviewed season template. Compatibility and coverage cannot be qualified
without those bytes. No charts, roster, era-rule assumptions, source contract,
calibration profile or historical-fit claim were created. No expensive tuning,
season campaign or generator changes were started.

The concrete next dependency is an accessible 1977 PFR HTML/source bundle with
provenance, or another reviewed compatible public feed. Then census all games
and required fields, retain the two announced gaps, and decide explicitly how
missing events enter the modeled scope before generating a candidate. The
existing fumble modeling/exclusion policies do not automatically resolve missing
stretches of ordinary play-by-play. An affordable addition still requires the
existing source/chart gates and complete historical season validation; do not
publish aggregate fallback as a reconstruction of unavailable play-by-play.

Local acquisition receipts remain in ignored
`.ai-audits/release-readiness/v1.10.3/1977-feasibility/`. No downloaded raw source
or historical narrative is committed. This note adds no player-facing behavior,
so player/API guides and packaging do not change.
