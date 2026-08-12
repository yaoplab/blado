# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Blado/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('BladoCommon', 'BladoCommon'), ('phibuilder', 'phibuilder'), ('photos', 'photos'), ('sql', 'sql')],
    hiddenimports=['configparser', 'PySide6.QtSvg'],
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
    a.binaries,
    a.datas,
    [],
    name='BladoSetup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
