# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for EQUELLA Bulk Importer (EBI)

This file defines how PyInstaller should build the EBI executable.
It specifies all dependencies, data files, and build options.

Usage:
    pyinstaller ebi.spec
    
Or use the setup.py wrapper:
    python setup.py
"""

import os
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Path to source files - use the main source directory, not package-win-linux
source_dir = os.path.join(os.path.dirname(spec_dir), 'source')

# (Importing ebi here is avoided to prevent DLL load issues during PyInstaller analysis)

# Explicitly collect all wx native shared libs so PyInstaller bundles them correctly
# on all architectures where auto-detection may miss wx runtime libraries.
wx_binaries = collect_dynamic_libs('wx')

block_cipher = None

# Collect all data files (images, icons, properties)
datas = [
    (os.path.join(source_dir, 'ebi.properties'), '.'),
    (os.path.join(source_dir, 'ebismall.ico'), '.'),
    (os.path.join(source_dir, 'ebibig.ico'), '.'),
    (os.path.join(source_dir, 'fileopen.png'), '.'),
    (os.path.join(source_dir, 'filesave.png'), '.'),
    (os.path.join(source_dir, 'gtk-stop.png'), '.'),
    (os.path.join(source_dir, 'gtk-help.png'), '.'),
    (os.path.join(source_dir, 'options.png'), '.'),
    (os.path.join(source_dir, 'pause.png'), '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'wx',
    'wx.grid',
    'wx.html',
    'wx.lib.wordwrap',
    'configparser',
    'html.parser',
    'xml.etree.ElementTree',
    'webbrowser',
    'http.server',
    'http.client',
    'json',
    'pathlib',
    'urllib.request',
    'urllib.parse',
    'urllib.error',
    'threading',
]

a = Analysis(
    [os.path.join(source_dir, 'ebi.py')],
    pathex=[source_dir],
    binaries=wx_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ebi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(source_dir, 'ebismall.ico'),
    version_file=None,
)

# One-dir mode: place the exe and all shared libs in a folder.
# More reliable across different Linux distributions and mount types.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ebi',
)
# To create a version info file, use:
# pyi-grab_version <some_exe.exe>
# Then edit and reference it above
