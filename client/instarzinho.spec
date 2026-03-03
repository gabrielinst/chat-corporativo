# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Instarzinho (Jurídico)

import os

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('api_client.py', '.'),
        ('assets/robo.png', 'assets'),
    ],
    hiddenimports=['PyQt6.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Instarzinho',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sem janela do terminal
    disable_windowed_traceback=False,
    icon=None,
    argv_emulation=False,
)
