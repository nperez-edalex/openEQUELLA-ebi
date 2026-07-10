# EBI Executable Packaging Guide

## Overview

This guide explains how to package the EBI application as a Windows executable with the settings UI dialog.

## Architecture

```
ebi_app.exe
  ├── Tkinter UI (settings dialog)
  ├── SettingsManager (config file in %APPDATA%)
  ├── EBILauncher (orchestration)
  ├── TLEClient (REST API client)
  └── Dependencies (requests, urllib, etc.)
```

## Setup

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

### 2. File Structure

Your project should have:

```
openEQUELLA-ebi/
├── source/
│   ├── ebi_launcher.py           # Main entry point
│   ├── equella_settings.py        # Settings management
│   ├── equella_settings_ui.py     # Tkinter UI dialog
│   ├── equellaclient_rest.py      # REST client
│   └── equellaclient41.py         # Legacy compatibility
├── build_executable.spec          # PyInstaller spec file (see below)
└── EXECUTABLE_PACKAGING_GUIDE.md  # This file
```

### 3. Create PyInstaller Spec File

Create `build_executable.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for EBI application

block_cipher = None

a = Analysis(
    ['source/ebi_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['tkinter'],
    hookspath=[],
    runtime_hooks=[],
    excludedimports=[],
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
    name='ebi_importer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for GUI-only (no console window)
    icon='icon.ico',  # Optional: path to your application icon
)
```

### 4. Build the Executable

```bash
pyinstaller build_executable.spec
```

The executable will be created in the `dist/` folder:
```
dist/
└── ebi_importer.exe
```

## Running the Executable

### First Run (Configuration)

When users run the executable for the first time:

1. The application checks if settings exist in `%APPDATA%\EBI\settings.json`
2. If not found, the **Settings Dialog** automatically opens
3. User configures:
   - Institution URL
   - OAuth Client ID (recommended) OR REST Token
   - Optional settings (debug mode, etc.)
4. Settings are saved and application proceeds

### Subsequent Runs

- Settings are automatically loaded from `%APPDATA%\EBI\settings.json`
- OAuth implicit grant opens browser automatically for authentication
- User logs in and approves access in browser
- Token is captured automatically and used for API calls
- Application proceeds with operations

## Usage Examples

### Example 1: Basic Import Script

```python
# custom_importer.py
from ebi_launcher import EBILauncher

def import_items(client):
    """Your custom import logic."""
    collections = client._enumerateItemDefs()
    print(f"Found {len(collections)} collections")
    # ... rest of your import logic

if __name__ == "__main__":
    launcher = EBILauncher()
    launcher.run_import(import_items)
```

Then package as:
```bash
pyinstaller --onefile --windowed --icon=icon.ico \
    --add-data "source:." \
    custom_importer.py
```

### Example 2: Headless/Automated

For automated processes (scheduled tasks, CI/CD):

```python
from ebi_launcher import EBILauncher

launcher = EBILauncher()

# Skip configuration check if you're confident settings exist
if launcher.settings.is_configured():
    client = launcher.create_client()
    # Run your import...
else:
    print("Settings not configured. Run interactive EBI app first.")
    sys.exit(1)
```

## Configuration File

After first run, settings are stored in:

**Windows:**
```
%APPDATA%\EBI\settings.json
```

Example content:
```json
{
  "institution_url": "https://equella.institution.edu",
  "oauth_client_id": "abc123def456",
  "oauth_redirect_uri": "default",
  "rest_access_token": "",
  "rest_admin_token": "",
  "debug": false
}
```

Users can edit this file directly (while application is closed) to:
- Change institution URL
- Switch authentication method
- Enable debug mode
- Clear tokens

## Authentication Flows

### Flow 1: OAuth Implicit Grant (Default)

```
User runs ebi_importer.exe
    ↓
Settings loaded from %APPDATA%\EBI\settings.json
    ↓
Check if OAuth Client ID is configured
    ↓ Yes
Browser opens to OAuth authorization endpoint
    ↓
User logs in (in browser)
    ↓
User approves "EBI" application
    ↓
Browser redirects with token in URL fragment
    ↓
Local HTTP server captures token
    ↓
Token stored in memory and used for REST API calls
    ↓
Application proceeds
```

### Flow 2: Pre-obtained Token

```
User runs ebi_importer.exe
    ↓
Settings loaded from %APPDATA%\EBI\settings.json
    ↓
REST Access Token found in settings
    ↓
Token used directly for REST API calls (no browser)
    ↓
Application proceeds
```

### Flow 3: Cookie Session (Fallback)

```
User runs ebi_importer.exe
    ↓
Settings loaded
    ↓
No OAuth Client ID or tokens configured
    ↓
Fall back to form-post login
    ↓
Username/password from settings used for login
    ↓
Session cookie established
    ↓
Application proceeds
```

## Troubleshooting

### Settings Dialog Doesn't Open

**Problem:** Application exits without showing dialog

**Solutions:**
- Ensure tkinter is included in PyInstaller spec (`hiddenimports=['tkinter']`)
- Check that `equella_settings_ui.py` is in the same directory as exe
- Try running from command line to see error messages

### Browser Doesn't Open

**Problem:** OAuth dialog doesn't open browser automatically

**Solutions:**
- Check Windows registry for default browser
- Run from command line with `--debug` flag
- Manually enter the OAuth URL in your browser
- Use custom redirect URI and paste token manually

### Token Not Captured

**Problem:** Browser opens but token isn't captured

**Solutions:**
- Ensure port 9999 is not blocked by firewall
- Try different port in `_capture_implicit_grant_token_via_server(port=XXXX)`
- Check institution URL is accessible
- Enable debug mode to see detailed logging

### Settings File Issues

**Problem:** Settings file corrupted or can't be read

**Solutions:**
- Delete `%APPDATA%\EBI\settings.json` to force reconfiguration
- Check file permissions on `%APPDATA%\EBI\` directory
- Ensure JSON is valid (use online JSON validator)

## Advanced Configuration

### Customize Icon

1. Prepare an `.ico` file (e.g., `icon.ico`)
2. Update spec file:
   ```python
   exe = EXE(..., icon='icon.ico')
   ```
3. Rebuild executable

### Single File Executable

Add `--onefile` flag:
```bash
pyinstaller --onefile build_executable.spec
```

This creates a single `.exe` file (slower startup, easier distribution).

### No Console Window

For GUI-only applications, set in spec file:
```python
exe = EXE(..., console=False)
```

Or use PyInstaller flag:
```bash
pyinstaller --windowed build_executable.spec
```

### Signed Executable

For enterprise distribution, sign the executable:
```bash
signtool sign /f certificate.pfx /p password /t http://timestamp.server \
    dist/ebi_importer.exe
```

## Distribution

### For End Users

1. Create installer using NSIS, Inno Setup, or similar
2. Installer places exe in `Program Files\EBI\`
3. Create Start Menu shortcut
4. First run shows settings dialog
5. Users configure institution URL and OAuth client ID
6. Ready to use

### For Internal/Automated Use

1. Copy exe to network share or application server
2. Pre-populate `%APPDATA%\EBI\settings.json` via GPO or script
3. Users run exe without configuration dialog

## Security Notes

- Tokens are cached in memory during runtime only
- Settings file includes OAuth client ID but not secrets
- Use HTTPS for institution URLs
- Restrict access to `%APPDATA%\EBI\` directory on shared machines
- Tokens should be revoked in openEQUELLA if credentials are compromised

## Migration from Command-Line

If users previously ran the importer via command-line with environment variables:

**Before:**
```bash
set EBI_REST_ACCESS_TOKEN=token123
set EBI_OAUTH_CLIENT_ID=client456
python import.py
```

**After:**
1. Run `ebi_importer.exe`
2. Settings dialog opens
3. Enter OAuth Client ID and Institution URL
4. Settings saved to `%APPDATA%\EBI\settings.json`
5. Token captured automatically on next run

Environment variables still work for backward compatibility but are overridden by saved settings.

## Next Steps

1. Update your import script to use `EBILauncher`
2. Test with `python ebi_launcher.py`
3. Build executable: `pyinstaller build_executable.spec`
4. Test the exe from command line
5. Create installer if needed
