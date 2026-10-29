# -*- mode: python ; coding: utf-8 -*-

# BuildOffice Pro packaging configuration.
# Keep runtime resources outside Python imports so the source application
# and packaged application use the same folder structure.

from pathlib import Path

ROOT = Path(SPECPATH)

# Runtime resources required by the existing application.
# Deliberately exclude config/developer_mode.json: source builds may use it
# for development, while release builds must fall back to the normal security gate.
datas = [
    (str(ROOT / "resources"), "resources"),
    (str(ROOT / "translations"), "translations"),
    (str(ROOT / "VERSION"), "."),
]

a = Analysis(
    ['BuildOffice Pro.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BuildOffice Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BuildOffice Pro',
)
