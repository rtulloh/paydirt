# Paydirt Football Board Game Simulation

A Python implementation of the classic Paydirt football board game, originally published by Avalon Hill.
Call the plays, manage the clock, and take on a computer opponent in your browser or terminal.

![Paydirt game screen](docs/images/kickoff-and-scoreboard.png)

## Features

- Chart-and-dice play resolution, penalties, and special teams.
- Three CPU difficulty levels, with player coaching in Easy mode.
- Season-specific conversion and overtime rules.
- Interactive CLI saves and season standings; browser play history and saved replays.
- Support for your own team charts and seasons.

## Download & Install

Download the latest build from [GitHub Releases](https://github.com/rtulloh/paydirt/releases):

| Platform | Download |
|----------|----------|
| macOS, Apple Silicon | `Paydirt-X.X.X-arm64.dmg` |
| macOS, Intel | `Paydirt-X.X.X-x86_64.dmg` |
| Windows | `PaydirtSetup.exe` or portable `paydirt.exe` |
| Linux | `Paydirt-x86_64.AppImage` |

Launch the application to open the browser interface. Select **New Game**, choose your teams and
which side to control, then follow the coin toss and play-selection prompts.

See [installation and troubleshooting](docs/installation.md) for platform details.

## Play the CLI from Source

Requires **Python 3.10+**. From a repository checkout:

```sh
git clone https://github.com/rtulloh/paydirt.git
cd paydirt
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyyaml
python -m paydirt --play --compact
```

On Windows, activate the environment with `.venv\Scripts\Activate.ps1` in PowerShell.
Use `-d easy` for coaching, or `-d hard` for a more aggressive opponent.
Use `python -m paydirt --help` to see available commands.

The browser interface needs additional dependencies and a frontend build when running from source;
see [web development setup](paydirt-web/README.md).

## Teams and Seasons

The public sample season contains the fictional **2026 Thunderhawks and Ironclads**.
Historical charts are not distributed with the project; supply your own data that you have permission to use.

[Add seasons and configure rules](docs/seasons.md), or use the
[chart generator / Excel importer](docs/chart-generator.md) to convert existing `.xls` charts into CSV files.

## Documentation

Start at the [documentation index](docs/README.md), or jump to a topic:

| For players | For contributors |
|-------------|------------------|
| [Browser walkthrough](docs/web-interface.md) | [Development, testing, and packaging](docs/development.md) |
| [CLI controls, rules, and strategy](docs/playing.md) | [Web development setup](paydirt-web/README.md) |
| [Clock management](docs/clock-management.md) | [AI play-testing notes](docs/dev-notes/ai-playtesting.md) |
| [AI difficulty and coaching](docs/ai-difficulty.md) | [Replay debugging design notes](docs/dev-notes/replayable-game-logs.md) |
| [Saved games and standings](docs/saved-games-and-standings.md) | [Release notes](RELEASE_NOTES.md) |
| [Seasons and chart files](docs/seasons.md) | [Contributor/agent instructions](AGENTS.md) |
| [Chart generator tool](docs/chart-generator.md) | [Full-game browser regression](paydirt-web/frontend/e2e/README.md) |

The app's **User Guide** includes the player guides for offline reading.

## License

This is a fan-made implementation for educational purposes. Paydirt is a trademark of its respective owners.
