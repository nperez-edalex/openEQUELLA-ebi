# -*- mode: python ; coding: utf-8 -*-
# This is a PyInstaller spec file for building the EBI executable application
#
# Usage: pyinstaller build_executable.spec
#
# For single-file executable: pyinstaller --onefile build_executable.spec
# For GUI-only (no console): pyinstaller --windowed build_executable.spec

import sys
from pathlib import Path

# Get the source directory
source_dir = Path(__file__).parent / 'source'

block_cipher = None

a = Analysis(
    [str(source_dir / 'ebi_launcher.py')],
    pathex=[str(source_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ebi_importer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False if you want GUI-only (no console window)
    icon=None,     # Set to 'icon.ico' if you have an icon file
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Optional: Create a single-file executable instead of directory
# Uncomment the section below and comment out the exe = EXE(...) section above
# to create a single .exe file (slower startup time)

# onefile = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='ebi_importer_onefile',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=True,
#     icon=None,
# )

# If you want to create a .zip distribution as well, uncomment:
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='ebi_importer'
# )

print("""
PyInstaller configuration complete!

To build the executable, run:
    pyinstaller build_executable.spec

The executable will be created in the 'dist' folder.

For single-file executable:
    pyinstaller --onefile build_executable.spec

For GUI-only (no console window):
    pyinstaller --windowed build_executable.spec

For both single-file and windowed:
    pyinstaller --onefile --windowed build_executable.spec
""")
