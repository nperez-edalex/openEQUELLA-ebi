# EBI Executable Quick Start Guide

## What You Now Have

A complete Python application that:
- ✅ Has a user-friendly Settings dialog (UI)
- ✅ Saves configuration to a local file (`%APPDATA%\EBI\settings.json`)
- ✅ Supports OAuth implicit grant authentication
- ✅ Can be packaged as a Windows executable
- ✅ Works without environment variables

## 5-Minute Setup

### Step 1: Test Locally First (Optional)

Before packaging as executable, test the settings dialog:

```bash
# From the source directory
python -m equella_settings_ui
```

You should see the Settings Dialog. Test filling it out, then close.

### Step 2: Register OAuth Client in openEQUELLA

1. Log in to your openEQUELLA institution
2. Go to **Settings → Integration → OAuth**
3. Click **Register new client application**
4. Fill in:
   - **Descriptive name:** `EBI Importer` (or any name)
   - **OAuth flow:** Select `Implicit Grant`
   - **Redirect URL:** Leave as default (recommended)
   - **Token validity:** `30` days (or your preference)
5. Click **SAVE**
6. **Copy the Client ID** (you'll need this)

### Step 3: Build the Executable

```bash
# Install PyInstaller if you haven't already
pip install pyinstaller

# Build from project root
pyinstaller build_executable.spec
```

Wait for build to complete. The executable is in `dist/ebi_importer.exe`

### Step 4: Run the Executable

Double-click `dist/ebi_importer.exe` (or run from command line)

First run will show the Settings Dialog:

1. **Institution URL:** `https://equella.your-institution.edu` (no trailing slash)
2. **OAuth Client ID:** Paste the Client ID from Step 2
3. **OAuth Redirect URI:** Leave blank (uses default)
4. Click **Save**

### Step 5: Authorization

After saving settings:

1. A browser window opens automatically
2. You see openEQUELLA login screen
3. Enter your credentials
4. Click authorize
5. Browser shows "Authorization successful!"
6. Close the browser
7. Back in command prompt, application proceeds

✅ **Done!** Application is now configured and authenticated.

## What Happens on Next Run

Next time you run `ebi_importer.exe`:

1. Opens browser automatically
2. Shows openEQUELLA authorization screen
3. You approve access (no login needed if already logged in to openEQUELLA)
4. Token captured automatically
5. Application proceeds

**No settings dialog needed** — configuration is saved!

## Accessing Settings Dialog Later

To change settings or re-configure:

### Option A: Delete Settings File
```
Delete: %APPDATA%\EBI\settings.json
```
Next run will show settings dialog.

### Option B: Edit Settings File
```
Location: %APPDATA%\EBI\settings.json

Edit directly to change:
- Institution URL
- OAuth Client ID
- Token (if using manual token)
- Debug mode
```

### Option C: Add Menu Item (If Your App Has UI)

In your application code:
```python
from ebi_launcher import EBILauncher

launcher = EBILauncher()

# Show settings dialog anytime
if launcher.show_settings():
    print("Settings updated!")
```

## File Structure

After building, you'll have:

```
openEQUELLA-ebi/
├── dist/
│   └── ebi_importer.exe         ← Run this!
├── build/
│   └── ebi_importer/            ← Ignore (temp build files)
├── source/
│   ├── ebi_launcher.py
│   ├── equella_settings.py
│   ├── equella_settings_ui.py
│   └── equellaclient_rest.py
├── build_executable.spec
├── QUICK_START.md               ← You are here
├── OAUTH_IMPLICIT_GRANT_GUIDE.md
└── EXECUTABLE_PACKAGING_GUIDE.md
```

## Common Tasks

### Task: Change Institution URL

```
1. Open: %APPDATA%\EBI\settings.json
2. Change "institution_url" value
3. Save file
4. Run ebi_importer.exe
```

### Task: Use Different OAuth Client

```
1. Open: %APPDATA%\EBI\settings.json
2. Change "oauth_client_id" to new client ID
3. Save file
4. Run ebi_importer.exe (will request new authorization)
```

### Task: Use Manual Token Instead of OAuth

```
1. Obtain a token from openEQUELLA
   (Settings → Integration → OAuth → Generated tokens)
2. Open: %APPDATA%\EBI\settings.json
3. Set "rest_access_token" to your token UUID
4. Save file
5. Run ebi_importer.exe (no browser will open)
```

### Task: Enable Debug Mode

```
1. Open: %APPDATA%\EBI\settings.json
2. Change "debug" to: true
3. Save file
4. Run ebi_importer.exe (will show detailed logs)
```

### Task: Distribute to Other Users

**Option A: Share settings template**
```json
{
  "institution_url": "https://equella.your-institution.edu",
  "oauth_client_id": "YOUR_CLIENT_ID_HERE",
  "oauth_redirect_uri": "default",
  "rest_access_token": "",
  "rest_admin_token": "",
  "debug": false
}
```

Send to users as `%APPDATA%\EBI\settings.json` template

**Option B: Pre-populate via script**
```batch
@echo off
mkdir "%APPDATA%\EBI"
copy settings.json "%APPDATA%\EBI\settings.json"
ebi_importer.exe
```

## Troubleshooting

### Problem: "Institution URL not provided and not configured"

**Solution:** Run the executable. Settings dialog will appear. Fill in Institution URL and save.

### Problem: Settings dialog won't open

**Solutions:**
- Ensure you're running the .exe (not Python script)
- Check that `equella_settings_ui.py` is in the same folder as `.exe`
- Try from command line to see error: `ebi_importer.exe`

### Problem: Browser doesn't open for OAuth

**Solutions:**
1. Try manually visiting the OAuth URL:
   ```
   https://equella.your-institution.edu/oauth/authorise?response_type=token&client_id=YOUR_CLIENT_ID&redirect_uri=default
   ```

2. Or use manual token method:
   - Get token from openEQUELLA settings
   - Set `rest_access_token` in `%APPDATA%\EBI\settings.json`

### Problem: "No session cookie returned"

**This shouldn't happen with OAuth!** But if it does:
1. Check OAuth Client ID is correct
2. Check institution URL is correct
3. Try manual token method (above)

### Problem: Settings file is corrupt/unreadable

**Solution:**
```
1. Delete: %APPDATA%\EBI\settings.json
2. Run ebi_importer.exe
3. Reconfigure settings
```

## Next Steps

### For Your Team:
1. Test `ebi_importer.exe` locally
2. Create installer (using NSIS, Inno Setup, etc.)
3. Distribute to team members
4. Document your specific workflows

### For Development:
- See `EXECUTABLE_PACKAGING_GUIDE.md` for advanced configuration
- See `OAUTH_IMPLICIT_GRANT_GUIDE.md` for OAuth details
- Modify `ebi_launcher.py` to add your specific logic

## Support

**Settings Dialog Issues?**
- Check `equella_settings_ui.py` (Tkinter UI code)

**REST Client Issues?**
- Check `equellaclient_rest.py` (API client code)
- Enable debug mode to see details

**OAuth Issues?**
- Check `OAUTH_IMPLICIT_GRANT_GUIDE.md`
- Verify OAuth client is configured in openEQUELLA

**Packaging Issues?**
- Check `EXECUTABLE_PACKAGING_GUIDE.md`
- Verify Python 3.8+ installed
- Verify PyInstaller installed: `pip install pyinstaller`

---

**Ready to go!** Run `ebi_importer.exe` and enjoy the UI-based configuration! 🎉
