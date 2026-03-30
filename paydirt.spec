# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Include seasons, LICENSE, and web static files
datas = [
    ('seasons/2026', 'seasons/2026'),
    ('seasons/samples', 'seasons/samples'),
    ('LICENSE', '.'),
    # Include web static files
    ('paydirt-web/backend/web_static', 'web_static'),
    # Include web backend Python files explicitly
    ('paydirt-web/backend/main.py', 'paydirt-web/backend/main.py'),
    ('paydirt-web/backend/routes.py', 'paydirt-web/backend/routes.py'),
    ('paydirt-web/backend/__init__.py', 'paydirt-web/backend/__init__.py'),
]

from PyInstaller.utils.hooks import collect_all

# Collect all uvicorn dependencies
datas_uvicorn, binaries_uvicorn, hiddenimports_uvicorn = collect_all('uvicorn')
datas_fastapi, binaries_fastapi, hiddenimports_fastapi = collect_all('fastapi')
datas_starlette, binaries_starlette, hiddenimports_starlette = collect_all('starlette')
datas_pydantic, binaries_pydantic, hiddenimports_pydantic = collect_all('pydantic')

# Combine all collected data
all_datas = datas + datas_uvicorn + datas_fastapi + datas_starlette + datas_pydantic
all_binaries = binaries_uvicorn + binaries_fastapi + binaries_starlette + binaries_pydantic
all_hiddenimports = hiddenimports_uvicorn + hiddenimports_fastapi + hiddenimports_starlette + hiddenimports_pydantic

a = Analysis(
    ['paydirt_runner.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports + [
        'yaml', 'pkg_resources', 'msvcrt', 'winreg', '_winapi', 'nt', 'typing_extensions',
        'python_multipart',
        'wsproto', 'wsproto.extensions', 'wsproto.frame',
        'httptools', 'httptools.parser', 'httptools.parser.http_parser',
    ],
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