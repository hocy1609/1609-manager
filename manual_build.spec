# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Collecting all submodules to ensure nothing is missed
hidden_imports = []
hidden_imports.extend(collect_submodules('core'))
hidden_imports.extend(collect_submodules('ui'))
hidden_imports.extend(collect_submodules('utils'))
# Explicitly add the module that was missing
hidden_imports.append('core.log_monitor_manager')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'), 
        ('logo.ico', '.'),
        ('nwn_settings.example.json', '.'),
        ('assets', 'assets'),
    ],
    hiddenimports=hidden_imports,
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
    [],
    exclude_binaries=True,
    name='1609Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='1609Manager',
)
