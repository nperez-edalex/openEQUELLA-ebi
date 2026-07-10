#Boa:Dialog:OptionsDialog

# Author: Jim Kurian, Pearson plc.
# Date: October 2014
#
# EBI Preferences dialog. Requires MainFrame.py to launch it.

import sys, wx, os, keyword, re
import wx.stc as stc

def create(parent):
    return OptionsDialog(parent)

[wxID_OPTIONSDIALOG] = [wx.NewId() for _init_ctrls in range(1)]

class BasicPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

class AdvancedPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

class AuthPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

class OptionsDialog(wx.Dialog):
    def _init_ctrls(self, prnt):
        wx.Dialog.__init__(self, style=wx.DEFAULT_DIALOG_STYLE, name='', parent=prnt, title='Preferences', pos=wx.Point(-1, -1), id=wxID_OPTIONSDIALOG, size=wx.Size(440, 350))

        # notebook (tabs)
        self.nb = wx.Notebook(parent=self, pos=wx.Point(0, 47))
        self.basicPage = BasicPage(self.nb)
        self.nb.AddPage(self.basicPage, "Basic")
        self.advancedPage = AdvancedPage(self.nb)
        self.nb.AddPage(self.advancedPage, "Advanced")
        self.authPage = AuthPage(self.nb)
        self.nb.AddPage(self.authPage, "OAuth/Auth")  

        self.mainBoxSizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.mainBoxSizer.Add(self.nb, 1, border=0, flag=wx.EXPAND)
        self.SetSizer(self.mainBoxSizer)

        padding = 5
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.AddSpacer(10)   

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkLoadLastSettingsFile = wx.CheckBox(parent=self.basicPage, id=-1, label='Load last settings file when starting EBI', style=0)
        self.chkLoadLastSettingsFile.SetValue(False)
        box.Add(self.chkLoadLastSettingsFile, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        sizer.Add(box, 0, wx.ALL, padding)
 
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkClearLogEachRun = wx.CheckBox(parent=self.basicPage, id=-1, label="Clear log each run", style=0)
        self.chkClearLogEachRun.SetValue(False)
        self.chkClearLogEachRun.SetToolTip("Clear log at the start of each run")
        box.Add(self.chkClearLogEachRun, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        sizer.Add(box, 0, wx.ALL, padding)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkSavePassword = wx.CheckBox(parent=self.basicPage, id=-1, label="Save password in settings file", style=0)
        self.chkSavePassword.SetValue(True)
        self.chkSavePassword.SetToolTip("Save password in settings file")
        box.Add(self.chkSavePassword, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        sizer.Add(box, 0, wx.ALL, padding)
        
        sizer.AddSpacer(3)
                
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.basicPage, -1, "Log buffer size (lines):")
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        self.txtLogBufferSize = wx.TextCtrl(self.basicPage, -1, "", size=wx.Size(60,-1))
        box.Add(self.txtLogBufferSize)
        sizer.Add(box, 0, wx.ALL, padding)        
        
        self.basicPage.SetSizer(sizer)
        
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.AddSpacer(10)   


        gridSizer = wx.FlexGridSizer(cols=2, vgap=0, hgap=0)

        label = wx.StaticText(id=-1, label='Proxy Server Address:', parent=self.advancedPage, style=wx.ALIGN_RIGHT)
        gridSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 4)
        self.txtProxyAddress = wx.TextCtrl(id=-1,
              name='txtProxyAddress', parent=self.advancedPage,
              size=wx.Size(280, 21), style=0, value='')
        self.txtProxyAddress.SetToolTip('Proxy address e.g. "delphi_proxy:8080"')
        gridSizer.Add(self.txtProxyAddress)

        gridSizer.AddSpacer(5)
        gridSizer.AddSpacer(5)

        label = wx.StaticText(id=-1, label='Proxy Server Username:', parent=self.advancedPage, style=wx.ALIGN_RIGHT)
        gridSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 4)
        self.txtProxyUsername = wx.TextCtrl(id=-1,
              name='txtProxyUsername', parent=self.advancedPage,
              size=wx.Size(150, 21), style=0)
        gridSizer.Add(self.txtProxyUsername)
        
        gridSizer.AddSpacer(5)
        gridSizer.AddSpacer(5)

        label = wx.StaticText(id=-1, label='Proxy Server Password:', parent=self.advancedPage, style=wx.ALIGN_RIGHT)
        gridSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 4)
        self.txtProxyPassword = wx.TextCtrl(id=-1,
              name='txtProxyPassword', parent=self.advancedPage,
              size=wx.Size(150, 21), style=wx.TE_PASSWORD)
        gridSizer.Add(self.txtProxyPassword)

        sizer.Add(gridSizer, 0, wx.ALL, padding)
        
        sizer.AddSpacer(15)   
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkDebugMode = wx.CheckBox(parent=self.advancedPage, id=-1, label='Debug Mode', style=0)
        self.chkDebugMode.SetValue(False)
        box.Add(self.chkDebugMode, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        sizer.Add(box, 0, wx.ALL, padding)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkNetworkLogging = wx.CheckBox(parent=self.advancedPage, id=-1, label='Network Logging (Warning: only use for small runs)', style=0)
        self.chkNetworkLogging.SetValue(False)
        box.Add(self.chkNetworkLogging, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        sizer.Add(box, 0, wx.ALL, padding)
        
        sizer.AddSpacer(3)   

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.advancedPage, -1, "Attachment chunk size (bytes):")
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        self.txtAttachmentsChunkSize = wx.TextCtrl(self.advancedPage, -1, "", size=wx.Size(80,-1))
        box.Add(self.txtAttachmentsChunkSize)
        sizer.Add(box, 0, wx.ALL, padding)

        self.advancedPage.SetSizer(sizer)

        # OAuth/Auth tab
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(10)

        # Institution URL
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.authPage, -1, "Institution URL:", style=wx.ALIGN_RIGHT)
        label.SetMinSize(wx.Size(150, -1))
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        self.txtInstitutionUrl = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(250, 21))
        self.txtInstitutionUrl.SetToolTip('e.g., https://equella.your-institution.edu (no trailing slash)')
        box.Add(self.txtInstitutionUrl, 1, wx.ALL|wx.EXPAND, padding)
        sizer.Add(box, 0, wx.ALL|wx.EXPAND, 0)

        sizer.AddSpacer(10)

        # OAuth Client ID
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.authPage, -1, "OAuth Client ID:", style=wx.ALIGN_RIGHT)
        label.SetMinSize(wx.Size(150, -1))
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        self.txtOAuthClientId = wx.TextCtrl(self.authPage, -1, "", size=wx.Size(250, 21))
        self.txtOAuthClientId.SetToolTip('From openEQUELLA Settings → Integration → OAuth')
        box.Add(self.txtOAuthClientId, 1, wx.ALL|wx.EXPAND, padding)
        sizer.Add(box, 0, wx.ALL|wx.EXPAND, 0)

        sizer.AddSpacer(10)

        # OAuth Redirect URI
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.authPage, -1, "OAuth Redirect URI:", style=wx.ALIGN_RIGHT)
        label.SetMinSize(wx.Size(150, -1))
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, padding)
        self.txtOAuthRedirectUri = wx.TextCtrl(self.authPage, -1, "default", size=wx.Size(250, 21))
        self.txtOAuthRedirectUri.SetToolTip('Leave as "default" for automatic token capture')
        box.Add(self.txtOAuthRedirectUri, 1, wx.ALL|wx.EXPAND, padding)
        sizer.Add(box, 0, wx.ALL|wx.EXPAND, 0)

        sizer.AddStretchSpacer()
        self.authPage.SetSizer(sizer)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        self.mainBoxSizer.Add(btnsizer, 0, wx.RIGHT|wx.ALL, 5)


    def __init__(self, parent):
        self.startScript = ""
        self.endScript = ""        
        self.preScript = ""
        self.postScript = ""        
        self._init_ctrls(parent)

