# Historical season source coverage

Provider coverage checked November 8, 2026; local acquisition status updated
November 9, 2026. This is a source-selection reference for future season work,
not a claim that every listed season is ready to generate or release.

## Provider coverage

| Seasons | PFR play-by-play coverage statement | Practical meaning for Paydirt |
| --- | --- | --- |
| Before 1977, including 1972 | Full season-wide PBP is not included in PFR's advertised coverage. Individual Super Bowls are a separate exception. Aggregate team/player and box-score statistics extend further back. | Do not feed aggregate-only pages to the full-PBP generator or present modeled fallback as observed play distributions. Additional sources or an explicitly reviewed aggregate model are needed. |
| 1977 | PBP added August 12, 2026, with missing portions of two games. | All 196 regular-season pages are now cached and parse. Partial-game gaps and reviewed modeling/exclusions remain; acquisition is distinct from qualification. |
| 1978–1993 | PFR's August 2025 expansion added these seasons and described regular/postseason coverage back to 1978 with a 4:47 gap in one game. | Candidate seasons for the PFR path; acquire and census the actual source pages first. The expansion's completeness caveat must not be erased. |
| 1994–1998 | PFR reports these were within its PBP coverage before the 2025 expansion. | Candidate PFR seasons; local acquisition and validation still required. |
| 1999–2025 | Within PFR's advertised PBP range; nflverse also supports this era. | Prefer the existing nflverse acquisition path when it supplies the needed complete inputs. No untested season is automatically qualified. |
| 2026 | Within the advertised modern range, but the season is in progress at this checkpoint. | Treat any real-season charts as dated snapshots of completed games, not a final season. The fictional public 2026 test teams remain separate. |

Sources: PFR's [coverage documentation](https://www.pro-football-reference.com/about/coverage.htm),
Sports Reference's [2025 expansion announcement](https://www.sports-reference.com/blog/2025/08/massive-expansion-of-play-by-play-and-stats-on-pro-football-reference/),
and its [1977 announcement](https://www.sports-reference.com/blog/2026/08/1977-play-by-play-and-associated-stats-added-to-pro-football-reference/).
The maintained [nflreadr PBP loader](https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R)
sets 1999 as its first supported season.

PFR's advertised range is **1977 onward**, not just 1983. Calling every season
strictly complete would overstate the evidence: the provider discloses gaps, and
we have not independently inventoried every season. The 2025 statement is a dated
provider claim, not a fresh current-game completeness audit.

## Known coverage caveats

The 1977 announcement lists missing late play segments in Washington–Atlanta
in Week 2 (final 1:30) and St. Louis–Washington in Week 13 (final 3:55 of the
second quarter plus part of the fourth). It also discloses uncertain forced-fumble
attribution. That attribution uncertainty does not automatically imply unknown
fumble recovery or missing ordinary plays; inspect the fields the generator needs.

The 2025 expansion announcement identifies one 4:47 gap in the older coverage.
This reference does not assign that caveat to a season without a verified
per-game inventory, or claim that it has since been repaired. PBP-derived totals
can also differ from subsequently corrected official statistics. Availability,
complete game coverage and statistical reconciliation are separate checks.

## What Paydirt has actually acquired

| Season | Local evidence | Chart status |
| --- | --- | --- |
| 1983 | Cached source inventory has 233 game pages; the established generation cohort used all 224 regular-season games. A freshly fetched archived control parses 163 play rows. Later official-gamebook review and explicit modeled fumble policies address ambiguous facts. | Generated charts are published. This is not a claim that every historical play is unambiguous or represented exactly. |
| 1977 | All 196 regular-season pages were acquired through the owner browser, hashed, parsed and checked against schedule/team/score identities. A reusable local cache is complete at the game-page level; known partial-game PBP gaps remain. | All 28 teams have a reproducible modeled candidate, not a qualified release. Reviewed source scope preserves exclusions and discrepancies; candidate-05 still misses Washington interception fit. See the current feasibility record and DATA-046. |
| 1972 | A sampled archived box score is accessible but has no PBP table; full season-wide PFR PBP is not advertised. | No PBP-generated season. Aggregate modeling remains separate deferred work. |
| 2024 | Existing acquisition/generation uses nflverse rather than PFR. | Generated charts are published. |
| Other years | Provider ranges above only; no complete local inventory is established by this document. | Not qualified by this reference. |

The earlier November 8 archive-only checkpoint found four usable pilot pages and
recent CDX entries for 22 of 196 regular games (174 absent from that returned
inventory). Those are historical acquisition findings, superseded by the complete
browser cache; they never established that PFR lacked the remaining games.

See [1977 feasibility and archive receipts](1977-season-feasibility.md),
[pre-1977 modeling backlog](issues/DATA/DATA-045.md), and
[chart attribution](../../CHART_ATTRIBUTION.md). Local raw pages, source hashes
and detailed receipts stay in ignored audit storage; do not commit the raw data.

## Why 1983 access does not guarantee another season

The archived pages must contain the PBP version of the site. PFR added 1978–1993
in August 2025 and 1977 in August 2026. A 2026 snapshot can therefore contain
1983 plays while still containing only summary statistics for 1977. Wayback can
redirect a requested date to an older capture, and HTTP/HTTPS variants can resolve
differently. Check final replay URL, capture date, content hash, actual PBP table
and parsed rows; never infer empirical coverage from HTTP 200 or a timestamp alone.
Current direct PFR requests also returned HTTP 403 in our bounded checks.

## Checklist before selecting a release season

1. Verify provider coverage and known partial-game omissions.
2. Acquire a small, varied pilot; confirm real source bytes parse and classify.
3. Inventory every expected game and actual PBP table. Check era membership,
   regular/postseason boundaries, aggregates, and missing required source facts.
4. Establish a reusable cache and provenance. Agree explicitly on any remaining
   modeling or exclusion policy before all-team generation.
5. Generate and audit staged charts, source fit, era rules and season behavior.
   Availability alone does not waive the existing validation or release checks.

Do not launch expensive generation, manual reconstruction or repeated-season
campaigns merely because a year falls inside a provider's advertised range.
