# Saved Games and Standings

[Documentation index](README.md) · [CLI controls](playing.md)

## Web Games and Campaigns

The web application saves a full engine checkpoint after acknowledged game actions. **Save Game**
also writes the current checkpoint. **Saved games** lists named exhibitions and campaign fixtures;
select **Resume** to continue, or **View final** for a finished game. Checkpoints retain both teams'
chart years, the governing rules, game/AI state, supported pending decisions, statistics, and history.
A pending coin toss reopens as a coin toss. A saved final does not count again in campaign standings.

For a completed campaign save, **Review recorded result** compares the saved engine final with
the season's accepted result. Confirm to replace that result and recompute standings and team
statistics; the prior result remains in correction history. Cancel leaves it unchanged. This
control uses the checkpoint's final score and statistics rather than manual score entry.
Results that have already fed a postseason bracket cannot be corrected through this flow.

Wait for **Saved in this browser** or **Saved in this application**, including its timestamp.
If storage fails, the executed play still
appears, the previous committed save is retained, and further plays stop until you retry the save
or explicitly restore a recoverable checkpoint. Never repeat a play merely because saving failed.
A stale tab must reopen the latest save before acting. Writable sessions require a current
browser with Web Locks, served over HTTPS or localhost; concurrent tabs cannot act on the
same game or season at the same time.

If another tab owns the game, kickoff and point-after controls show an error without
sending the action to the engine. Finish that tab's action, then retry. An automatic
CPU point-after offers **Retry automatic try** when its action was rejected; a pending
save failure must be resolved before that retry can run.

Use **Export** in Saved games, or **Export season** in Seasons, for a portable JSON backup.
Exporting a linked fixture exports its whole season; import that file from Seasons so its
schedule, results and active games stay together. Imports
are validated, and missing/changed chart editions or rules produce an error rather than silently
substituting another team year. Season exports include active fixture checkpoints; importing creates
a separate campaign and remaps its linked identities. No chart files or private source material
are embedded. Keep the referenced compatible charts available at the destination.

Browser-owned saves survive ordinary browser restarts in the same origin/profile. Clearing site data,
private browsing, a different browser/device, or an application origin change are separate boundaries.
Export before the machine reset. Browser storage does not provide cross-device sync or guarantee
offline engine installation. Older display-only web saves/replays remain a legacy flow and cannot
promise the completeness of the new engine checkpoints. CLI saves remain their separate supported format.

In **Saved games**, **Protect local saves** asks a supporting browser to protect browser-owned
games and seasons from automatic storage cleanup. This happens only when you click it. A refusal
does not remove your saves; keep exported backups. Protection cannot prevent explicit site-data deletion.

The installed application stores its library in `library.sqlite3` in the platform's Paydirt
user-data directory: `~/Library/Application Support/Paydirt/` on macOS,
`%LOCALAPPDATA%\Paydirt\` on Windows, and `~/.local/share/Paydirt/` on Linux (or
`$XDG_DATA_HOME/Paydirt/`). Its saves survive backend restarts and a change of application port;
clearing browser site data does not delete this application library. Export remains the portable
backup route. Only one native backend can own a library at a time; close that application before
opening another instance. Use the exact `127.0.0.1` URL printed/opened by the launcher.

A source backend uses browser-owned storage by default. To opt into a local application library,
set `PAYDIRT_NATIVE_USER_DATA_DIR` to a private user-data directory and
`PAYDIRT_NATIVE_FRONTEND_ORIGIN` to the exact frontend origin (default
`http://127.0.0.1:8000`). The native library accepts loopback clients only and rejects other
browser origins before mutations. This local mode does not provide shared hosted accounts or
remote storage. Do not copy a live SQLite database as your only backup; use Export or stop the
application before copying its user-data directory.

## Saving a CLI Game

At offensive or defensive play selection, enter **`W`** to write a save.
The CLI prints the actual save path. The default filename is `paydirt_save.json`;
keep a copy if you want multiple saved games rather than overwriting the default.

A save includes score, clock, field position, down/distance, possession, remaining timeouts,
statistics, scoring history, and supported game/AI state. It relies on the referenced team charts remaining available;
a save is not a way to distribute those charts. It also preserves an unresolved
in-play own-end-zone interception decision together with the dice state captured
when the choice was deferred. There is no pre-game end-zone return preference in
the browser game. Older saves without the newer keys restore automatic touchbacks
for direct engine compatibility.

## Resuming a CLI Game

Put `--load` first, optionally followed by a filename:

```sh
python -m paydirt --load --compact
python -m paydirt --load /path/to/paydirt_save.json --compact -d medium
```

Do not use the old `--play --load` example: the entry point dispatches loading separately.
Use the same local charts and compatible game version. Saving an unfinished CLI game is different from
saving browser play history; see [browser replays](web-interface.md#play-history-and-replays).
A resumed game is not a promise of bit-for-bit future RNG replay.
If a save owes a point-after attempt or safety free kick, the engine records
that follow-up explicitly. Resuming never adds touchdown or safety points a
second time, and an end-zone field position alone is not a pending score.
Preparing a kickoff or free kick does not discharge it; the marker persists
until the kick itself executes, so saving between setup and the kick resumes
correctly. A completed score with no owed action stays complete on reload.

## Recording Season Results

After an interactive game, the CLI offers to record the final result in season standings.
Choose whether to persist it. Use `--week N` to specify the week:

```sh
python -m paydirt --play --week 1 --compact
```

## Viewing and Managing Standings

From the repository root:

```sh
python -m paydirt.standings show 2026
python -m paydirt.standings games 2026
```

The games listing numbers recorded results in week order, preserving entry order within each week.
Use those numbers when editing or deleting; run the listing again after changing a week or deleting a game:

```sh
python -m paydirt.standings edit 2026 1 --home-score 31
python -m paydirt.standings delete 2026 1
```

These commands alter saved results. Check the season and game number, and back up your standings before making changes.
Standings display depends on the configured division structure; custom teams may require a matching division definition.
The standalone full-season regression runner never saves standings and does not populate your played season.

Restored play logs retain the pre-snap quarter and clock and the engine-confirmed kickoff origin, including deferred penalties and safety free kicks.


### When a save needs attention

An acknowledged play can finish even if its checkpoint cannot be saved. Further
plays pause until that save succeeds, so the game cannot silently run ahead of
its recoverable state. A failed play request displays its error in the game panel.
Keep the tab open and use the save-status retry control or **Save game** after
resolving the problem. Reloading restores the last successful save and may omit
an unsaved play. A native library error retains the previous committed save.

The main menu’s **Load game** shortcut opens the same durable **Saved games**
library. It no longer reconstructs a game from older local-storage display data.
Any older local-storage data is retained; the shortcut does not migrate it into
a season checkpoint.

Pending field-goal penalties keep the kick context and the unresolved coaching
choice in the checkpoint. Resuming returns to the same accept/decline choice;
loading a save does not decide the penalty for you.
