# Saved Games and Standings

[Documentation index](README.md) · [CLI controls](playing.md)

## Saving a CLI Game

At offensive or defensive play selection, enter **`W`** to write a save.
The CLI prints the actual save path. The default filename is `paydirt_save.json`;
keep a copy if you want multiple saved games rather than overwriting the default.

A save includes score, clock, field position, down/distance, possession, remaining timeouts,
statistics, scoring history, and supported game/AI state. It relies on the referenced team charts remaining available;
a save is not a way to distribute those charts.

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

The games listing numbers recorded results. Use those numbers when editing or deleting:

```sh
python -m paydirt.standings edit 2026 1 --home-score 31
python -m paydirt.standings delete 2026 1
```

These commands alter saved results. Check the season and game number, and back up your standings before making changes.
Standings display depends on the configured division structure; custom teams may require a matching division definition.
The standalone full-season regression runner never saves standings and does not populate your played season.
