# wxPython Integration Guide: OAuth Settings

This guide shows how to integrate OAuth implicit grant authentication with your existing wxPython GUI application.

## Files Involved

- `source/equella_settings.py` — **New** Settings persistence (already created)
- `source/equellaclient_rest.py` — **Updated** REST client with OAuth support (already updated)
- `source/OptionsDialog.py` — **Modify** Add OAuth fields
- `source/MainFrame.py` — **Modify** Use SettingsManager for OAuth
- `package-win/ebi.spec` — **Modify** Update PyInstaller config

## Step 1: Update OptionsDialog.py

Add an "OAuth/Auth" tab to your preferences dialog to configure authentication.

**Location:** After the AdvancedPage definition in OptionsDialog.py, add:

```python
class AuthPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
```

**In the `_init_ctrls` method, after the Advanced tab is added:**

```python
# Create Auth/OAuth tab (add this after self.advancedPage section)
self.authPage = AuthPage(self.nb)
self.nb.AddPage(self.authPage, "OAuth/Auth")

# Build Auth page UI
sizer = wx.BoxSizer(wx.VERTICAL)
sizer.AddSpacer(10)

# Institution URL
box = wx.BoxSizer(wx.HORIZONTAL)
label = wx.StaticText(self.authPage, -1, "Institution URL:", style=wx.ALIGN_RIGHT)
box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
self.txtInstitutionUrl = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(300, 21))
self.txtInstitutionUrl.SetToolTip('e.g., https://equella.your-institution.edu (no trailing slash)')
box.Add(self.txtInstitutionUrl, 1, wx.ALL|wx.EXPAND, 5)
sizer.Add(box, 0, wx.ALL|wx.EXPAND, 5)

sizer.AddSpacer(10)

# OAuth Client ID
box = wx.BoxSizer(wx.HORIZONTAL)
label = wx.StaticText(self.authPage, -1, "OAuth Client ID:", style=wx.ALIGN_RIGHT)
box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
self.txtOAuthClientId = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(300, 21))
self.txtOAuthClientId.SetToolTip('From openEQUELLA Settings → Integration → OAuth')
box.Add(self.txtOAuthClientId, 1, wx.ALL|wx.EXPAND, 5)
sizer.Add(box, 0, wx.ALL|wx.EXPAND, 5)

sizer.AddSpacer(10)

# OAuth Redirect URI
box = wx.BoxSizer(wx.HORIZONTAL)
label = wx.StaticText(self.authPage, -1, "OAuth Redirect URI:", style=wx.ALIGN_RIGHT)
box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
self.txtOAuthRedirectUri = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(300, 21))
self.txtOAuthRedirectUri.SetToolTip('Leave empty for default (recommended)')
box.Add(self.txtOAuthRedirectUri, 1, wx.ALL|wx.EXPAND, 5)
sizer.Add(box, 0, wx.ALL|wx.EXPAND, 5)

sizer.AddSpacer(15)

# REST Access Token (alternative auth method)
box = wx.BoxSizer(wx.HORIZONTAL)
label = wx.StaticText(self.authPage, -1, "REST Access Token:", style=wx.ALIGN_RIGHT)
box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
self.txtRestAccessToken = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(300, 21), style=wx.TE_PASSWORD)
self.txtRestAccessToken.SetToolTip('Optional: Pre-obtained OAuth token UUID')
box.Add(self.txtRestAccessToken, 1, wx.ALL|wx.EXPAND, 5)
sizer.Add(box, 0, wx.ALL|wx.EXPAND, 5)

sizer.AddSpacer(10)

# REST Admin Token
box = wx.BoxSizer(wx.HORIZONTAL)
label = wx.StaticText(self.authPage, -1, "REST Admin Token:", style=wx.ALIGN_RIGHT)
box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
self.txtRestAdminToken = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(300, 21), style=wx.TE_PASSWORD)
self.txtRestAdminToken.SetToolTip('Optional: Admin token for import operations')
box.Add(self.txtRestAdminToken, 1, wx.ALL|wx.EXPAND, 5)
sizer.Add(box, 0, wx.ALL|wx.EXPAND, 5)

self.authPage.SetSizer(sizer)
```

## Step 2: Update equellaclient_rest.py

The REST client already has OAuth support. Just ensure it uses SettingsManager:

**In `source/equellaclient_rest.py`, check that it has:**

```python
from equella_settings import SettingsManager

class TLEClient:
    def __init__(
        self,
        owner,
        institutionUrl="",
        username="",
        password="",
        ...
        settings_manager=None,
    ):
        self.settings = settings_manager or SettingsManager()
        
        # Load from settings if not provided
        if not institutionUrl:
            institutionUrl = self.settings.get("institution_url", "")
        
        # Load OAuth settings
        self._oauth_client_id = (
            self.settings.get("oauth_client_id", "").strip()
            or os.environ.get("EBI_OAUTH_CLIENT_ID", "").strip()
        )
        self._oauth_redirect_uri = (
            self.settings.get("oauth_redirect_uri", "").strip()
            or os.environ.get("EBI_OAUTH_REDIRECT_URI", "").strip()
        )
        
        # Try OAuth before cookie session
        if not (self._rest_access_token or self._rest_admin_token):
            if self._oauth_client_id:
                try:
                    self._establish_implicit_grant_session()
                except Exception as oauth_error:
                    if self.debug:
                        print(f"OAuth failed: {oauth_error}. Falling back to cookie session.")
                    self._establish_cookie_session()
            else:
                self._establish_cookie_session()
```

✅ **This is already done in the updated equellaclient_rest.py**

## Step 3: Update MainFrame.py

Integrate SettingsManager into your Engine initialization.

**In your MainFrame class where you create the Engine, update:**

```python
# At the top of MainFrame.py, add import:
from equella_settings import SettingsManager

# In your method that creates the Engine:
def createEngine(self, version, copyright, license, downloadpage, propertiesfile):
    # Initialize settings manager
    self.settingsManager = SettingsManager()
    
    # Create engine with settings
    self.engine = Engine.create(
        self,
        version,
        copyright,
        license,
        downloadpage,
        propertiesfile,
        settings_manager=self.settingsManager
    )
    
# When creating TLEClient for REST calls:
client = TLEClient(
    owner="EBI",
    institutionUrl=institution_url,  # From settings file
    username=username,
    password=password,
    debug=debug,
    settings_manager=self.settingsManager  # Pass settings manager
)
```

## Step 4: Update Your Settings File Handler

Your current code saves/loads from `.ebi` files. The SettingsManager creates persistent OAuth settings in `%APPDATA%\EBI\settings.json`.

When loading a `.ebi` settings file, also load any saved OAuth settings:

```python
def loadSettings(self, path):
    # Existing code to load .ebi file...
    try:
        # Load OAuth settings from persistent storage
        oauth_client_id = self.settingsManager.get("oauth_client_id", "")
        oauth_redirect_uri = self.settingsManager.get("oauth_redirect_uri", "")
        
        # Pre-populate OAuth fields in dialog if they exist
        if oauth_client_id:
            self.optionsDialog.txtOAuthClientId.SetValue(oauth_client_id)
        if oauth_redirect_uri:
            self.optionsDialog.txtOAuthRedirectUri.SetValue(oauth_redirect_uri)
```

## Step 5: Save OAuth Settings

When user clicks OK in preferences dialog:

```python
def OnPreferences(self, event):
    dlg = OptionsDialog.create(self)
    
    if dlg.ShowModal() == wx.ID_OK:
        # Save OAuth settings to persistent storage
        self.settingsManager.set("institution_url", dlg.txtInstitutionUrl.GetValue())
        self.settingsManager.set("oauth_client_id", dlg.txtOAuthClientId.GetValue())
        self.settingsManager.set("oauth_redirect_uri", dlg.txtOAuthRedirectUri.GetValue())
        self.settingsManager.set("rest_access_token", dlg.txtRestAccessToken.GetValue())
        self.settingsManager.set("rest_admin_token", dlg.txtRestAdminToken.GetValue())
        self.settingsManager.save()
        
        # Save to .ebi settings file as before
        # ... your existing save code ...
```

## Step 6: Update PyInstaller Spec

Ensure your `package-win/ebi.spec` includes necessary imports:

```python
hiddenimports = [
    'wx',
    'wx.grid',
    'wx.html',
    'wx.lib.wordwrap',
    'configparser',
    'html.parser',
    'xml.etree.ElementTree',
    'json',
    'pathlib',
    'urllib.request',
    'http.server',
    'webbrowser',
]
```

## Step 7: Update Engine.py

If Engine.py creates TLEClient, pass the settings manager:

```python
def __init__(self, ...., settings_manager=None):
    self.settings_manager = settings_manager or SettingsManager()
    ...

def createClient(self, institution_url, username, password, proxy=""):
    return TLEClient(
        owner="EBI",
        institutionUrl=institution_url,
        username=username,
        password=password,
        proxy=proxy,
        debug=self.debug,
        settings_manager=self.settings_manager
    )
```

## How It Works

### User Workflow

1. **First run:** User opens Preferences → OAuth/Auth tab
2. **User enters:**
   - Institution URL
   - OAuth Client ID (from openEQUELLA settings)
   - Optional: OAuth Redirect URI or REST Token
3. **User clicks OK:** Settings saved to `%APPDATA%\EBI\settings.json`
4. **Next run:** When starting import, browser opens for OAuth authorization
5. **Token captured:** Automatically used for REST API calls

### OAuth Flow

```
Settings Dialog
    ↓
Save to %APPDATA%\EBI\settings.json
    ↓
Engine creates TLEClient with settings_manager
    ↓
TLEClient loads OAuth settings
    ↓
Browser opens to OAuth endpoint
    ↓
User logs in and approves
    ↓
Token captured and used for API calls
```

## Configuration Storage

Settings are stored in:
```
%APPDATA%\EBI\settings.json
```

Example:
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

## Testing

1. **Test locally:**
   ```bash
   python source/ebi.py
   ```

2. **Open Preferences (if you have menu item)**
   - Fill in OAuth settings
   - Click OK
   - Check `%APPDATA%\EBI\settings.json` to verify settings saved

3. **Test OAuth flow:**
   - Start an import
   - Browser should open
   - Log in to openEQUELLA
   - Approve access
   - Token should be captured

4. **Build executable:**
   ```bash
   cd package-win
   package.bat
   ```

## Backward Compatibility

- Existing `.ebi` settings files still work
- Environment variables (`EBI_OAUTH_CLIENT_ID`, etc.) still work
- Settings dialog is optional (users can use environment variables)
- Falls back to cookie session if OAuth fails

## Troubleshooting

### Settings not saving
- Check that `%APPDATA%\EBI\` directory is writable
- Check JSON for syntax errors

### OAuth not working
- Verify OAuth Client ID is from openEQUELLA settings
- Verify Institution URL is correct
- Check browser window opened
- Enable debug mode to see detailed logs

### Browser won't open
- Check Windows default browser is set
- Check port 9999 is not blocked by firewall
- Use manual REST token as workaround

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `equella_settings.py` | **NEW** | Persistent settings storage |
| `equellaclient_rest.py` | Updated | OAuth support (already done) |
| `OptionsDialog.py` | Add Auth tab | UI for OAuth configuration |
| `MainFrame.py` | Initialize SettingsManager | Load/save OAuth settings |
| `Engine.py` | Pass settings_manager | TLEClient gets settings |
| `ebi.spec` | Add imports | Ensure webbrowser included |

---

**Next:** Follow the integration steps above, then run `package.bat` to build the executable!
