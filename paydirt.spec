# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Include seasons, LICENSE, and web static files
datas = [
    ('seasons/2026', 'seasons/2026'),
    ('seasons/samples', 'seasons/samples'),
    ('LICENSE', '.'),
    # Include web static files if they exist
    ('paydirt-web/backend/web_static', 'web_static'),
]

a = Analysis(
    ['paydirt_runner.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'yaml', 'pkg_resources', 'msvcrt', 'winreg', '_winapi', 'nt', 'typing_extensions',
        # Web dependencies
        'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops._autointerval',
        'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'fastapi', 'fastapi.middleware', 'fastapi.middleware.cors',
        'starlette', 'starlette.middleware', 'starlette.middleware.cors',
        'starlette.responses', 'starlette.routing',
        'pydantic', 'pydantic.main', 'pydantic.fields',
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