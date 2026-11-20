# Installation

[Documentation index](README.md) · Next: [browser interface](web-interface.md) or [CLI play](playing.md)

## Play Without Installing

[Play Paydirt in your browser](https://rtulloh.github.io/paydirt/) as the primary
play option. Internet access is needed to load the Python engine. Games and
seasons save in that browser profile and site; export important saves for backup
or transfer. See [browser controls](web-interface.md) and
[save storage boundaries](saved-games-and-standings.md).

## Optional Desktop Downloads

Get a build from [GitHub Releases](https://github.com/rtulloh/paydirt/releases).
Pre-built downloads include the browser interface, generated 1977, 1983 and 2024 seasons, and the public 2026 sample teams; Python and Node.js are not needed to play.

| Platform | File | Launch |
|----------|------|--------|
| macOS, Apple Silicon (M1 or later) | `Paydirt-X.X.X-arm64.dmg` | Open the disk image and install the app |
| macOS, Intel | `Paydirt-X.X.X-x86_64.dmg` | Open the disk image and install the app |
| Windows | `PaydirtSetup.exe` | Run the installer |
| Windows, portable | `paydirt.exe` | Run the executable |
| Linux | `Paydirt-x86_64.AppImage` | Make executable, then run |

Launch Paydirt to open its local browser interface. Choose New Game to begin.
See the [browser walkthrough](web-interface.md) for screenshots and controls.

### macOS Gatekeeper

The macOS app is ad-hoc signed, not Developer ID signed or notarized. A fresh
Safari download of v1.12.1 passed strict signature verification but was blocked
by Gatekeeper. A valid ad-hoc signature does not establish notarization or a
warning-free first launch. Use the [browser edition](https://rtulloh.github.io/paydirt/)
to play without installing the desktop app or changing macOS security settings.

### Linux AppImage

```sh
chmod +x Paydirt-x86_64.AppImage
./Paydirt-x86_64.AppImage
```

## Python Installation

The CLI requires **Python 3.10+** and **PyYAML**. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyyaml
python -m paydirt --play --compact
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
Use `python` in place of `python3` when that is your Python launcher.
These commands run directly from the checkout, where the sample season files are available.

**Use `--play` for the CLI.** Running `python -m paydirt` without arguments launches web mode,
which needs backend packages and a built frontend, not just PyYAML.
For that setup, see [web development](../paydirt-web/README.md).

## Installation Troubleshooting

- **No module named yaml:** install PyYAML with the same interpreter used to launch the game.
- **No teams appear:** check the [season directory structure](seasons.md), including its rules YAML.
- **Historical season missing:** it is not bundled; install your own authorized charts.
- **Source web interface unavailable:** use `--play` for terminal play, or follow the separate web setup guide.
- **Charts in Excel:** the app reads CSV charts. Use the [chart generator](chart-generator.md) first.
