# TradingOS PyInstaller spec file

import sys
import os

block_cipher = None

# Get the project root - spec file is in project root
project_root = os.getcwd()

a = Analysis(
    ['code/tradingos/__main__.py'],
    pathex=['code', project_root],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('config', 'config'),
        (os.path.join(project_root, 'config'), 'config'),
    ],
    hiddenimports=[
        'tradingos.core.config',
        'tradingos.core.events',
        'tradingos.core.health',
        'tradingos.core.logging',
        'tradingos.core.models',
        'tradingos.modules.scanner',
        'tradingos.modules.market',
        'tradingos.modules.charts',
        'tradingos.modules.indicators',
        'tradingos.modules.vision',
        'tradingos.modules.memory',
        'tradingos.modules.reasoning',
        'tradingos.modules.risk',
        'tradingos.modules.execution',
        'tradingos.modules.journal',
        'tradingos.modules.learning',
        'tradingos.modules.video',
        'tradingos.modules.dashboard',
        'numba',
        'numba.core',
        'numba.cuda',
        'llama_cpp',
        'onnxruntime',
        'qdrant_client',
        'duckdb',
        'polars',
        'fastapi',
        'uvicorn',
        'websockets',
        'watchfiles',
        'pydantic',
        'pydantic_settings',
        'yaml',
        'structlog',
        'orjson',
        'prometheus_client',
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
    name='tradingos',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)