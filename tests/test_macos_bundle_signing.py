"""Exercise bundle assembly with a strict, portable codesign command double."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "packaging/macos/create_app.sh"


@pytest.mark.parametrize("failure_stage", ["none", "sign", "verify"])
def test_finished_bundle_is_signed_and_verified_before_dmg_copy(
    tmp_path: Path, failure_stage: str,
) -> None:
    """The DMG must never receive an unsigned or unsuccessfully signed app."""
    commands = tmp_path / "commands"
    commands.mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/paydirt").write_text("synthetic executable", encoding="utf-8")
    for name in ("LICENSE", "CHART_ATTRIBUTION.md"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    codesign = commands / "codesign"
    codesign.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "bundle = pathlib.Path(args[-1])\n"
        "assert (bundle / 'Contents/Info.plist').is_file()\n"
        "assert (bundle / 'Contents/MacOS/paydirt').is_file()\n"
        "assert (bundle / 'Contents/Resources/LICENSE').is_file()\n"
        "assert (bundle / 'Contents/Resources/CHART_ATTRIBUTION.md').is_file()\n"
        "seal = bundle / 'Contents/_CodeSignature/CodeResources'\n"
        "if '--verify' in args:\n"
        "    assert '--deep' in args and '--strict' in args\n"
        "    assert seal.is_file()\n"
        "    if os.environ['FAIL_SIGNING'] == 'verify': sys.exit(24)\n"
        "else:\n"
        "    assert args[:-1] == ['--force', '--sign', '-', '--timestamp=none']\n"
        "    if os.environ['FAIL_SIGNING'] == 'sign': sys.exit(23)\n"
        "    seal.parent.mkdir()\n"
        "    seal.write_text('signed after resources')\n"
        "with open('signing.log', 'a') as log: log.write(' '.join(args[:-1]) + '\\n')\n",
        encoding="utf-8",
    )
    create_dmg = commands / "create-dmg"
    create_dmg.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, sys\n"
        "seal = pathlib.Path(sys.argv[-1]) / 'Paydirt.app/Contents/_CodeSignature/CodeResources'\n"
        "assert seal.is_file(), 'DMG received an unsigned bundle'\n"
        "assert pathlib.Path('signing.log').read_text().splitlines() == [\n"
        "    '--force --sign - --timestamp=none', '--verify --deep --strict']\n"
        "pathlib.Path('dmg-created').touch()\n",
        encoding="utf-8",
    )
    codesign.chmod(0o755)
    create_dmg.chmod(0o755)
    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True,
        env={**os.environ, "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}",
             "FAIL_SIGNING": failure_stage, "GITHUB_REF_NAME": "v1.12.1"},
        check=False,
    )
    if failure_stage != "none":
        assert result.returncode == {"sign": 23, "verify": 24}[failure_stage], result.stderr
        assert not (tmp_path / "dmg-created").exists()
    else:
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "dmg-created").exists()
