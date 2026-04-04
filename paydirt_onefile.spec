# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Include only the 2026 season directory
datas = [
    ('seasons/2026', 'seasons/2026'),
    # Include the MIT LICENSE and README files
    ('LICENSE', '.'),
    ('README.md', '.'),
    ('docs/images', 'docs/images'),
]

a = Analysis(
    ['paydirt_runner.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['yaml', 'pkg_resources'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='paydirt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)