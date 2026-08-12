# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

a = Analysis(
    ['Blado/__main__.py'],
    pathex=['D:/Blado'],
    binaries=[],
    datas=[
        ('BladoCommon', 'BladoCommon'),
        ('phibuilder', 'phibuilder'),
        ('photos', 'photos'),
        ('sql', 'sql'),
    ],
    hiddenimports=[
        'configparser', 'PySide6.QtSvg', 'PySide6.QtNetwork', 'PySide6.QtPrintSupport',
        'lxml', 'lxml.etree', 'docx', 'materialyoucolor', 'PIL', 'PIL.Image',
    ] + collect_submodules('psycopg2'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
a.binaries += collect_dynamic_libs('psycopg2')

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Blado',
    debug=False,
    console=False,
    disable_windowed_traceback=False,
)
