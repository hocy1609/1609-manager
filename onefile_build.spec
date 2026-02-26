# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import shutil
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# === Fixed paths ===
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
DIST_DIR = os.path.join(SPEC_DIR, 'dist')
WORK_DIR = os.path.join(SPEC_DIR, 'build', 'onefile_build')
SETTINGS_DIR = os.path.join(DIST_DIR, '1609 settings')
SETTINGS_BACKUP = os.path.join(SPEC_DIR, 'build', '_1609_settings_backup')

# Backup 1609 settings before build (PyInstaller may clean dist)
if os.path.exists(SETTINGS_DIR):
    if os.path.exists(SETTINGS_BACKUP):
        shutil.rmtree(SETTINGS_BACKUP)
    shutil.copytree(SETTINGS_DIR, SETTINGS_BACKUP)

# Restore hook - will be called after build
import atexit
def restore_settings():
    if os.path.exists(SETTINGS_BACKUP):
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(os.path.dirname(SETTINGS_DIR), exist_ok=True)
            shutil.copytree(SETTINGS_BACKUP, SETTINGS_DIR)
        shutil.rmtree(SETTINGS_BACKUP, ignore_errors=True)
atexit.register(restore_settings)

# Collecting all submodules
hidden_imports = []
hidden_imports.extend(collect_submodules('core'))
hidden_imports.extend(collect_submodules('ui'))
hidden_imports.extend(collect_submodules('utils'))
hidden_imports.append('core.log_monitor_manager')
hidden_imports.append('pystray')
hidden_imports.append('pystray.backend.win32')
hidden_imports.append('PIL')
hidden_imports.append('PIL.Image')
hidden_imports.append('PIL.ImageDraw')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join('Assets', 'logo.ico'), 'Assets'),
        ('nwn_settings.example.json', '.'),
        ('Assets', 'Assets'),
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='1609Manager',
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
    icon=os.path.join('Assets', 'logo.ico')
)
