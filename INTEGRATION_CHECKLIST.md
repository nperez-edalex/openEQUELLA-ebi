# OAuth Integration Checklist for wxPython App

## ✅ What's Already Done

- [x] `equella_settings.py` created — Settings persistence
- [x] `equellaclient_rest.py` updated — OAuth support built-in
- [x] `WXPYTHON_INTEGRATION_GUIDE.md` created — Step-by-step guide
- [x] Documentation complete

## 🎯 What You Need to Do

### Phase 1: Setup (5 minutes)

- [ ] **Register OAuth Client in openEQUELLA**
  - Go to Settings → Integration → OAuth
  - Click "Register new client application"
  - Select "Implicit Grant" flow
  - Copy the **Client ID**
  - Save the document with the Client ID

### Phase 2: Code Integration (30 minutes)

Follow the **WXPYTHON_INTEGRATION_GUIDE.md** in this order:

- [ ] **Step 1:** Add OAuth fields to `source/OptionsDialog.py`
  - Add AuthPage class
  - Add OAuth/Auth tab to notebook
  - Add text fields for: Institution URL, OAuth Client ID, Redirect URI, tokens
  - **Time:** ~10 min

- [ ] **Step 2:** Verify `source/equellaclient_rest.py`
  - Check it has `from equella_settings import SettingsManager`
  - Check OAuth initialization code exists
  - **Time:** ~2 min (should already be there)

- [ ] **Step 3:** Update `source/MainFrame.py`
  - Add `from equella_settings import SettingsManager` import
  - Initialize `self.settingsManager = SettingsManager()` in `createEngine()`
  - Pass `settings_manager=self.settingsManager` to TLEClient
  - **Time:** ~10 min

- [ ] **Step 4:** Update your settings file handler
  - Load OAuth settings when loading `.ebi` file
  - Pre-populate dialog fields with saved OAuth settings
  - **Time:** ~5 min

- [ ] **Step 5:** Add settings save handler
  - Save OAuth fields when user clicks OK in preferences
  - Call `self.settingsManager.save()`
  - **Time:** ~5 min

- [ ] **Step 6:** Update PyInstaller spec
  - Add `'webbrowser'`, `'http.server'`, `'json'`, `'pathlib'` to `hiddenimports`
  - **Time:** ~2 min

- [ ] **Step 7:** Update `source/Engine.py` (if it creates TLEClient)
  - Add `settings_manager` parameter
  - Pass to TLEClient initialization
  - **Time:** ~5 min

### Phase 3: Testing (15 minutes)

- [ ] **Test 1: Run locally**
  ```bash
  cd source
  python ebi.py
  ```
  - Open Preferences
  - Fill in OAuth settings
  - Click OK
  - Check `%APPDATA%\EBI\settings.json` to verify it was saved

- [ ] **Test 2: Verify settings file**
  - Open `%APPDATA%\EBI\settings.json`
  - Verify your OAuth Client ID is there
  - Verify Institution URL is there

- [ ] **Test 3: OAuth flow**
  - Start an import operation
  - Browser should open automatically
  - Log in to openEQUELLA
  - Click approve
  - Browser should show "Authorization successful"
  - Application should continue

- [ ] **Test 4: Build executable**
  ```bash
  cd package-win
  package.bat
  ```
  - Should complete without errors
  - Check `package-win/ebi/ebi.exe` exists

- [ ] **Test 5: Run executable**
  - Double-click `package-win/ebi/ebi.exe`
  - Open Preferences
  - Verify OAuth settings dialog works
  - Save settings
  - Start import and verify OAuth flow works

### Phase 4: Deployment (5 minutes)

- [ ] **Distribution**
  - Test on another machine if possible
  - Create installer or share `ebi.zip` from `package-win/`
  - Document that users need to configure OAuth settings on first run

## 📋 Quick Reference

### Files to Modify
```
source/
├── OptionsDialog.py          ← ADD Auth/OAuth tab
├── MainFrame.py              ← IMPORT SettingsManager, initialize it
├── Engine.py                 ← PASS settings_manager to TLEClient
└── equellaclient_rest.py    ← ALREADY DONE ✓

package-win/
└── ebi.spec                  ← ADD imports to hiddenimports
```

### Files Already Done
```
source/
├── equella_settings.py       ← NEW ✓
└── equellaclient_rest.py    ← UPDATED ✓

Documentation/
├── WXPYTHON_INTEGRATION_GUIDE.md ← REFERENCE THIS
├── QUICK_START.md
├── OAUTH_IMPLICIT_GRANT_GUIDE.md
└── EXECUTABLE_PACKAGING_GUIDE.md
```

## 🚨 Common Issues

### "SettingsManager not found"
- Ensure `equella_settings.py` is in `source/` directory
- Ensure import statement is: `from equella_settings import SettingsManager`

### Browser doesn't open
- Check Windows default browser is set
- Check port 9999 is not blocked
- Use REST token as workaround in preferences

### Settings not saving
- Check `%APPDATA%\EBI\` is writable
- Check JSON file is valid
- Enable debug mode to see errors

### OAuth fails with "Institution URL not found"
- Verify Institution URL is configured in preferences
- Verify it's correct (no trailing slash)
- Check it's accessible from your network

## 💾 Persistent Storage Locations

After integration, settings will be stored at:

**Windows:**
```
C:\Users\<username>\AppData\Roaming\EBI\settings.json
```

**macOS:**
```
~/.config/ebi/settings.json
```

**Linux:**
```
~/.config/ebi/settings.json
```

## 🎬 Expected User Flow After Integration

1. **First Launch:**
   - User runs `ebi.exe`
   - Opens Preferences
   - Enters Institution URL and OAuth Client ID
   - Clicks OK
   - Settings saved to `%APPDATA%\EBI\settings.json`

2. **Second Launch:**
   - User runs `ebi.exe`
   - Starts import
   - Browser opens automatically
   - User logs in (if not already) and approves
   - Token captured automatically
   - Import proceeds

3. **Subsequent Launches:**
   - Browser opens for quick re-auth
   - User approves (one click if already logged in)
   - Import proceeds

## ✨ Benefits After Integration

✅ No environment variables needed  
✅ Persistent configuration across runs  
✅ Browser-based OAuth (modern, secure)  
✅ Automatic token capture  
✅ Fallback to cookie session if needed  
✅ Works in executable (no Python runtime needed)  
✅ Settings UI is familiar wxPython  

## 📞 Support

If you get stuck on any step:

1. **Check the guide:** See `WXPYTHON_INTEGRATION_GUIDE.md` Step-by-step
2. **Check the code:** Look for commented examples in this checklist
3. **Enable debug:** Set `debug=True` in preferences to see detailed logs
4. **Check logs:** Look in console for error messages

---

## Summary

**Total Time Estimate:** ~50 minutes (5 min setup + 30 min code + 15 min testing)

**Difficulty:** Medium (familiar with wxPython already)

**Risk:** Low (backward compatible, existing tests still work)

**Next Action:** Start with Phase 2, Step 1 in `WXPYTHON_INTEGRATION_GUIDE.md`

Go! 🚀
