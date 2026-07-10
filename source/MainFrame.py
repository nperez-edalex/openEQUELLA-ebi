# Boa:Frame:MainFrame

# Author: Jim Kurian, Pearson plc.
# Date: October 2014
#
# Graphical user interface for the EQUELLA Bulk Importer. Utilizes
# wxPython to render an OS-native UI. Main purpose of the UI is to
# specify CSV settings, EQUELLA settings, save settings to file and start
# and stop import runs. Requires ebi.py to launch it.

import sys, time, keyword
import os, traceback
import wx
import wx.grid
import wx.stc as stc
import wx.adv
import OptionsDialog
import csv, codecs, io
import random, platform
import Engine
import Constants
import Utils
from xml.dom.minidom import Document, parse, parseString
import urllib.request, urllib.error, urllib.parse
import configparser
from equellaclient import *
from equella_settings import SettingsManager


def create(parent):
    return MainFrame(parent)


[
    wxID_MAINFRAME,
    wxID_MAINFRAMECOLUMNSGRID,
    wxID_MAINFRAMECONNECTIONPANEL,
    wxID_MAINFRAMEGRIDPANEL,
    wxID_MAINFRAMEMAINSTATUSBAR,
    wxID_MAINFRAMEMAINTOOLBAR,
    wxID_MAINFRAMETXTCSVPATH,
    wxID_MAINFRAMETXTPASSWORD,
    wxID_MAINFRAMETXTUSERNAME,
    wxID_MAINFRAMESTATICTEXT7,
    wxID_MAINFRAMELOGPANEL,
    wxID_MAINFRAMECSVPANEL,
] = [wx.NewId() for _init_ctrls in range(12)]

[
    wxID_MAINFRAMEMAINTOOLBARABOUT,
    wxID_MAINFRAMEMAINTOOLBAROPEN,
    wxID_MAINFRAMEMAINTOOLBARSAVE,
    wxID_MAINFRAMEMAINTOOLBARSTOP,
    wxID_MAINFRAMEMAINTOOLBARPAUSE,
    wxID_MAINFRAMEMAINTOOLBAROPTIONS,
] = [wx.NewId() for _init_coll_mainToolbar_Tools in range(6)]


class ConnectionPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)


class CSVPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)


class OptionsPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)


class LogPage(wx.Panel):
    def __init__(self, parent, owner):
        self.parent = parent
        self.owner = owner
        wx.Panel.__init__(self, parent)


class MainFrame(wx.Frame):

    def _init_coll_mainToolbar_Tools(self, parent):

        # generated method, don't edit
        parent.AddTool(
            wxID_MAINFRAMEMAINTOOLBAROPEN,
            "Open",
            wx.Bitmap(
                os.path.join(self.scriptFolder, "fileopen.png"), wx.BITMAP_TYPE_PNG
            ),
            shortHelp="Open Settings File",
            kind=wx.ITEM_NORMAL,
        )
        parent.AddTool(
            wxID_MAINFRAMEMAINTOOLBARSAVE,
            "Save",
            wx.Bitmap(
                os.path.join(self.scriptFolder, "filesave.png"), wx.BITMAP_TYPE_PNG
            ),
            shortHelp="Save Settings (" + self.ctrlButton + "+S)",
            kind=wx.ITEM_NORMAL,
        )
        parent.AddTool(
            wxID_MAINFRAMEMAINTOOLBARSTOP,
            "Stop",
            wx.Bitmap(
                os.path.join(self.scriptFolder, "gtk-stop.png"), wx.BITMAP_TYPE_PNG
            ),
            shortHelp="Stop Processing",
            kind=wx.ITEM_NORMAL,
        )
        parent.AddTool(
            wxID_MAINFRAMEMAINTOOLBARPAUSE,
            "Pause",
            wx.Bitmap(os.path.join(self.scriptFolder, "pause.png"), wx.BITMAP_TYPE_PNG),
            shortHelp="Pause/Unpause Processing",
            kind=wx.ITEM_NORMAL,
        )
        parent.AddTool(
            wxID_MAINFRAMEMAINTOOLBAROPTIONS,
            "Preferences",
            wx.Bitmap(
                os.path.join(self.scriptFolder, "options.png"), wx.BITMAP_TYPE_PNG
            ),
            shortHelp="Preferences",
            kind=wx.ITEM_NORMAL,
        )
        parent.AddTool(
            wxID_MAINFRAMEMAINTOOLBARABOUT,
            "About",
            wx.Bitmap(
                os.path.join(self.scriptFolder, "gtk-help.png"), wx.BITMAP_TYPE_PNG
            ),
            shortHelp="About EQUELLA Bulk Importer",
            kind=wx.ITEM_NORMAL,
        )
        self.Bind(
            wx.EVT_TOOL, self.OnMainToolbarSaveTool, id=wxID_MAINFRAMEMAINTOOLBARSAVE
        )
        self.Bind(
            wx.EVT_TOOL, self.OnMainToolbarSaveTool, id=wxID_MAINFRAMEMAINTOOLBAROPEN
        )
        self.Bind(
            wx.EVT_TOOL, self.OnMainToolbarSaveTool, id=wxID_MAINFRAMEMAINTOOLBARSTOP
        )
        self.Bind(
            wx.EVT_TOOL, self.OnMainToolbarSaveTool, id=wxID_MAINFRAMEMAINTOOLBARPAUSE
        )
        self.Bind(
            wx.EVT_TOOL, self.OnMainToolbarSaveTool, id=wxID_MAINFRAMEMAINTOOLBAROPTIONS
        )
        self.Bind(
            wx.EVT_TOOL, self.OnMainToolbarSaveTool, id=wxID_MAINFRAMEMAINTOOLBARABOUT
        )

        parent.Realize()

    def _init_coll_mainStatusBar_Fields(self, parent):
        # generated method, don't edit
        parent.SetFieldsCount(3)

        parent.SetStatusText("Ready", 0)
        parent.SetStatusText("", 1)
        parent.SetStatusText("", 2)

        parent.SetStatusWidths([-2, -1, -1])
        parent.SetMinHeight(30)

    def _init_sizers(self):
        # generated method, don't edit
        self.mainBoxSizer = wx.BoxSizer(orient=wx.VERTICAL)

        self.mainBoxSizer.Add(self.mainToolbar, 0, border=0, flag=wx.EXPAND)
        self.mainBoxSizer.Add(self.nb, 1, border=0, flag=wx.EXPAND)
        self.mainBoxSizer.Add(self.mainStatusBar, 0, border=0, flag=wx.EXPAND)
        self.SetSizer(self.mainBoxSizer)

    def _init_ctrls(self, prnt):

        # Handle PyInstaller bundle - use sys._MEIPASS for bundled data files
        if getattr(sys, "frozen", False):
            # Running as PyInstaller bundle
            self.scriptFolder = sys._MEIPASS
        else:
            # Running as script
            self.scriptFolder = sys.path[0]
            if self.scriptFolder.endswith(".zip"):
                self.scriptFolder = os.path.dirname(self.scriptFolder)

        # set ctrl or cmd tooltip depending on platform
        self.ctrlButton = "Ctrl"
        if platform.system() == "Darwin":
            self.ctrlButton = "Cmd"

        # generated method, don't edit
        wx.Frame.__init__(
            self,
            id=wxID_MAINFRAME,
            name="",
            parent=prnt,
            pos=wx.Point(617, 243),
            size=wx.Size(1022, 575),
            style=wx.DEFAULT_FRAME_STYLE,
            title="EQUELLA Bulk Importer",
        )
        self.SetClientSize(wx.Size(1012, 575))
        self.SetMinSize(wx.Size(1012, 575))
        self.SetAutoLayout(False)
        self.SetThemeEnabled(False)

        # notebook (tabs)
        self.nb = wx.Notebook(parent=self, pos=wx.Point(0, 47))
        self.connectionPage = ConnectionPage(self.nb)
        self.nb.AddPage(self.connectionPage, "Connection")
        self.csvPage = CSVPage(self.nb)
        self.nb.AddPage(self.csvPage, "CSV")
        self.optionsPage = OptionsPage(self.nb)
        self.nb.AddPage(self.optionsPage, "Options")
        self.logPage = LogPage(self.nb, self)
        self.nb.AddPage(self.logPage, "Log")

        self.columnsGrid = wx.grid.Grid(
            id=wxID_MAINFRAMECOLUMNSGRID,
            name="columnsGrid",
            parent=self.csvPage,
            pos=wx.Point(0, 125),
            size=wx.Size(1006, 281),
            style=0,
        )
        self.columnsGrid.SetToolTip("CSV column settings")
        self.columnsGrid.Bind(
            wx.grid.EVT_GRID_CELL_CHANGED, self.OnColumnsGridGridCellChange
        )

        self.log = Log(self.logPage)

        # Connection Page controls
        self.ConnectionSizer = wx.FlexGridSizer(cols=2, vgap=0, hgap=0)

        self.staticBox = wx.StaticBox(
            self.connectionPage, -1, "", size=wx.Size(600, 300)
        )
        self.borderBox = wx.StaticBoxSizer(self.staticBox, wx.VERTICAL)
        self.borderBox.Add(self.ConnectionSizer, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.connectionPage.SetSizer(self.ConnectionSizer)

        self.ConnectionSizer.AddSpacer(25)
        self.ConnectionSizer.AddSpacer(25)

        label = wx.StaticText(
            id=-1,
            label="Institution URL:",
            name="staticText1",
            parent=self.connectionPage,
            size=wx.Size(103, 17),
            style=wx.ALIGN_RIGHT,
        )
        self.ConnectionSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.txtInstitutionUrl = wx.TextCtrl(
            id=-1,
            name="txtInstitutionUrl",
            parent=self.connectionPage,
            size=wx.Size(422, 21),
            style=0,
            value="",
        )
        self.txtInstitutionUrl.SetHelpText(
            'Institution URL (e.g. "http://equella.myinstitution.edu/training")'
        )
        self.txtInstitutionUrl.SetToolTip(
            'EQUELLA institution URL (e.g. "http://equella.myinstitution.org/training")'
        )
        self.ConnectionSizer.Add(self.txtInstitutionUrl)

        label = wx.StaticText(
            id=-1,
            label="Username:",
            name="staticText1",
            parent=self.connectionPage,
            size=wx.Size(103, 17),
            style=wx.ALIGN_RIGHT,
        )
        self.ConnectionSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.txtUsername = wx.TextCtrl(
            id=wxID_MAINFRAMETXTUSERNAME,
            name="txtUsername",
            parent=self.connectionPage,
            pos=wx.Point(104, 27),
            size=wx.Size(155, 21),
            style=0,
            value="",
        )
        self.txtUsername.SetToolTip("EQUELLA username")
        self.ConnectionSizer.Add(self.txtUsername)

        label = wx.StaticText(
            id=-1,
            label="Password:",
            name="staticText1",
            parent=self.connectionPage,
            size=wx.Size(103, 17),
            style=wx.ALIGN_RIGHT,
        )
        self.ConnectionSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.txtPassword = wx.TextCtrl(
            id=wxID_MAINFRAMETXTPASSWORD,
            name="txtPassword",
            parent=self.connectionPage,
            pos=wx.Point(104, 52),
            size=wx.Size(155, 21),
            style=wx.TE_PASSWORD,
            value="",
        )
        self.txtPassword.Show(True)
        self.txtPassword.SetToolTip("EQUELLA password")
        self.ConnectionSizer.Add(self.txtPassword)

        label = wx.StaticText(
            id=-1,
            label="OAuth Client ID:",
            name="staticText1",
            parent=self.connectionPage,
            size=wx.Size(103, 17),
            style=wx.ALIGN_RIGHT,
        )
        self.ConnectionSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.txtOAuthClientId = wx.TextCtrl(
            id=-1,
            name="txtOAuthClientId",
            parent=self.connectionPage,
            size=wx.Size(422, 21),
            style=0,
            value="",
        )
        self.txtOAuthClientId.SetToolTip("OAuth Client ID (optional - required for OAuth authentication)")
        self.ConnectionSizer.Add(self.txtOAuthClientId)

        self.btnGetCollections = wx.Button(
            id=-1,
            label="Test / Get Collections",
            name="btnGetCollections",
            parent=self.connectionPage,
            pos=wx.Point(529, 2),
            size=wx.Size(155, 35),
            style=0,
        )
        self.btnGetCollections.SetToolTip(
            "Connect to EQUELLA and retrieve available collections"
        )
        self.btnGetCollections.Bind(wx.EVT_BUTTON, self.OnBtnGetCollectionsButton)
        self.ConnectionSizer.AddSpacer(15)
        self.ConnectionSizer.Add(self.btnGetCollections)

        self.ConnectionSizer.AddSpacer(15)
        self.ConnectionSizer.AddSpacer(15)

        label = wx.StaticText(
            id=-1,
            label="Collection:",
            name="staticText4",
            parent=self.connectionPage,
            size=wx.Size(103, 17),
            style=wx.ALIGN_RIGHT,
        )
        self.ConnectionSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.cmbCollections = wx.Choice(
            choices=[],
            id=-1,
            name="cmbCollections",
            parent=self.connectionPage,
            pos=wx.Point(309, 27),
            size=wx.Size(422, 21),
            style=0,
        )
        self.cmbCollections.SetToolTip("EQUELLA collection to import CSV content into")
        self.ConnectionSizer.Add(self.cmbCollections)

        # CSV Page controls
        self.CsvSizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.csvPage.SetSizer(self.CsvSizer)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.CsvSizer.Add(box)

        label = wx.StaticText(self.csvPage, -1, "CSV:")
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        self.txtCSVPath = wx.TextCtrl(
            id=wxID_MAINFRAMETXTCSVPATH,
            name="txtCSVPath",
            parent=self.csvPage,
            size=wx.Size(445, 21),
            style=0,
            value="",
        )
        self.txtCSVPath.SetToolTip("File path to CSV")
        box.Add(self.txtCSVPath, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        self.btnBrowseCSV = wx.Button(
            id=-1,
            label="Browse...",
            name="btnBrowseCSV",
            parent=self.csvPage,
            size=wx.Size(90, 23),
            style=0,
        )
        self.btnBrowseCSV.SetHelpText("Browse the computer for a CSV file")
        self.btnBrowseCSV.SetToolTip("Browse the computer for a CSV to load")
        self.btnBrowseCSV.Bind(wx.EVT_BUTTON, self.OnBtnBrowseCSVButton)
        box.Add(self.btnBrowseCSV, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        self.btnReloadCSV = wx.Button(
            id=-1,
            label="Reload CSV",
            name="btnReloadCSV",
            parent=self.csvPage,
            pos=wx.Point(846, 2),
            size=wx.Size(90, 23),
            style=0,
        )
        self.btnReloadCSV.SetHelpText(
            "Reload the CSV to update the settings for any column heading changes in the CSV"
        )
        self.btnReloadCSV.SetToolTip(
            "Reload the columns and update for any column heading changes in the CSV"
        )
        self.btnReloadCSV.Bind(wx.EVT_BUTTON, self.OnBtnReloadCSVButton, id=-1)
        box.Add(self.btnReloadCSV, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.CsvSizer.Add(box)

        label = wx.StaticText(self.csvPage, -1, "Encoding:")
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        self.cmbEncoding = wx.Choice(
            parent=self.csvPage,
            choices=[],
            id=-1,
            name="cmbEncoding",
            size=wx.Size(75, 21),
            style=0,
        )
        self.cmbEncoding.SetToolTip("Encoding used to read CSV file")
        box.Add(self.cmbEncoding, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        for encoding in self.encodingOptions:
            self.cmbEncoding.Append(encoding)
        self.cmbEncoding.SetSelection(0)
        self.CsvSizer.Add(self.columnsGrid, 1, wx.EXPAND)

        label = wx.StaticText(
            id=-1,
            label="Row filter:",
            name="staticText6",
            parent=self.csvPage,
            pos=wx.Point(753, 31),
            size=wx.Size(77, 13),
            style=wx.ALIGN_RIGHT,
        )
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        self.txtRowFilter = wx.TextCtrl(
            id=-1,
            name="txtRowFilter",
            parent=self.csvPage,
            pos=wx.Point(830, 27),
            size=wx.Size(158, 21),
            style=0,
            value="",
        )
        self.txtRowFilter.SetHelpText(
            'Restrict rows to be processed (e.g. "1,3,5-9,4")'
        )
        self.txtRowFilter.SetToolTip(
            'Restrict rows in the CSV to be processed (e.g. "2,3,7-12,4,1")'
        )
        box.Add(self.txtRowFilter, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        # options page
        labelWidth = 70
        indentWidth = 20
        padding = 4

        self.optionsSizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.optionsPage.SetSizer(self.optionsSizer)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(
            self.optionsPage,
            -1,
            "Use following base path for attachments (path to CSV directory used if left blank):",
        )
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, padding + 2)
        self.optionsSizer.Add(box, 0, wx.GROW | wx.ALL, 1)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.txtAttachmentsBasepath = wx.TextCtrl(
            self.optionsPage, -1, "", size=wx.Size(400, -1)
        )
        box.Add(self.txtAttachmentsBasepath, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        btnBrowseBasePath = wx.Button(
            id=-1,
            label="Browse...",
            name="btnBrowseBasePath",
            parent=self.optionsPage,
            size=wx.Size(88, 23),
            style=0,
        )
        box.Add(btnBrowseBasePath, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.OnBtnBrowseBasePath, btnBrowseBasePath)
        self.optionsSizer.Add(box, 0, wx.ALL, 1)

        self.chkSaveAsDraft = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Create new items and item versions in draft status (override DRAFT command)",
            name="chkSaveAsDraft",
            style=0,
        )
        self.chkSaveAsDraft.SetValue(False)
        self.chkSaveAsDraft.SetToolTip(
            "Create new items and new item versions in draft status (overrides DRAFT command option)"
        )
        self.optionsSizer.Add(self.chkSaveAsDraft, 0, wx.ALL, padding)

        self.chkSaveTestXml = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Save test XML",
            name="chkSaveTestXml",
            style=0,
        )
        self.chkSaveTestXml.SetValue(False)
        self.chkSaveTestXml.SetToolTip(
            "Output example XML files of item metadata from test imports"
        )
        self.optionsSizer.Add(self.chkSaveTestXml, 0, wx.ALL, padding)

        line = wx.StaticLine(
            self.optionsPage, -1, size=(20, -1), style=wx.LI_HORIZONTAL
        )
        self.optionsSizer.Add(line, 0, wx.GROW | wx.RIGHT | wx.TOP, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(
            self.optionsPage, -1, "When updating existing items:", size=(300, -1)
        )
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, padding)
        self.optionsSizer.Add(box, 0, wx.GROW | wx.TOP, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.optionsSizer.Add(box, 0, wx.ALL, padding)

        self.cmbExistingMetadataMode = wx.Choice(
            choices=[],
            id=-1,
            name="cmbExistingMetadataMode",
            parent=self.optionsPage,
            size=wx.Size(210, 21),
            style=0,
        )
        self.cmbExistingMetadataMode.Append("Clear all existing metadata")
        self.cmbExistingMetadataMode.Append("Replace only specified metadata")
        self.cmbExistingMetadataMode.Append("Append to existing metadata")
        self.cmbExistingMetadataMode.SetSelection(0)
        label = wx.StaticText(
            self.optionsPage,
            -1,
            "Existing Metadata:",
            size=(-1, -1),
            style=wx.ALIGN_RIGHT,
        )
        box.AddSpacer(indentWidth)
        box.Add(label, 0, wx.ALIGN_TOP | wx.ALL, padding)
        box.Add(self.cmbExistingMetadataMode, 1, wx.TOP | wx.ALL, padding)

        self.chkAppendAttachments = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Append Attachments",
            name="chkAppendAttachments",
            style=0,
        )
        self.chkAppendAttachments.SetValue(False)
        self.chkAppendAttachments.SetToolTip(
            "Leave attachments of existing items untouched and append specified attachments"
        )
        box.AddSpacer(indentWidth)
        box.Add(self.chkAppendAttachments, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 0)

        self.chkCreateNewVersions = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Create new versions",
            name="chkCreateNewVersions",
            style=0,
        )
        self.chkCreateNewVersions.SetValue(False)
        self.chkCreateNewVersions.SetToolTip(
            "When updating existing items create new versions (overrides VERSION command option)"
        )
        box.Add(
            self.chkCreateNewVersions, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, padding
        )

        line = wx.StaticLine(
            self.optionsPage, -1, size=(20, -1), style=wx.LI_HORIZONTAL
        )
        self.optionsSizer.Add(line, 0, wx.GROW | wx.RIGHT | wx.TOP, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(
            self.optionsPage,
            -1,
            "When specifying owners and collaborators:",
            size=(300, -1),
        )
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, padding)
        self.optionsSizer.Add(box, 0, wx.GROW | wx.TOP, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkUseEBIUsername = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Ignore owners that do not exist",
            name="chkUseEBIUsername",
            style=0,
        )
        self.chkUseEBIUsername.SetValue(False)
        self.chkUseEBIUsername.SetToolTip(
            "Ignore owners that do not exist (for 'Owner' column datatype)"
        )
        box.AddSpacer(indentWidth)
        box.Add(self.chkUseEBIUsername, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, padding)
        self.chkIgnoreNonexistentCollaborators = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Ignore collaborators that do not exist",
            name="chkIgnoreNonexistentCollaborators",
            style=0,
        )
        self.chkIgnoreNonexistentCollaborators.SetValue(False)
        self.chkIgnoreNonexistentCollaborators.SetToolTip(
            "Save item even if a specified collaborator does not exist"
        )
        box.AddSpacer(indentWidth)
        box.Add(
            self.chkIgnoreNonexistentCollaborators,
            1,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            padding,
        )
        self.optionsSizer.Add(box, 0, wx.ALL, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkSaveNonexistentUsernamesAsIDs = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Save usernames that are not internal users as user IDs (for LDAP users)",
            name="chkSaveNonexistentUsernamesAsIDs",
            style=0,
        )
        self.chkSaveNonexistentUsernamesAsIDs.SetValue(False)
        self.chkSaveNonexistentUsernamesAsIDs.SetToolTip(
            "Save usernames that are not internal users as user IDs (for LDAP users)"
        )
        box.AddSpacer(indentWidth)
        box.Add(
            self.chkSaveNonexistentUsernamesAsIDs,
            1,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            padding,
        )
        self.optionsSizer.Add(box, 0, wx.ALL, padding)

        line = wx.StaticLine(
            self.optionsPage, -1, size=(20, -1), style=wx.LI_HORIZONTAL
        )
        self.optionsSizer.Add(line, 0, wx.GROW | wx.RIGHT | wx.TOP, padding)

        gridSizer = wx.FlexGridSizer(cols=2, vgap=0, hgap=0)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.optionsPage, -1, "Export:", size=(300, -1))
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, padding)
        gridSizer.Add(box, 0, wx.GROW | wx.TOP, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.optionsPage, -1, "WHERE clause:", size=(300, -1))
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 0)
        gridSizer.Add(box, 0, wx.GROW | wx.TOP, 0)

        leftBox = wx.BoxSizer(wx.VERTICAL)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.chkExport = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Export items as CSV",
            name="chkExport",
            style=0,
        )
        self.chkExport.SetValue(False)
        self.chkExport.SetToolTip("Export items as CSV")
        box.AddSpacer(indentWidth)
        box.Add(self.chkExport, 1, wx.ALIGN_TOP | wx.ALL, padding)
        box.AddSpacer(indentWidth)
        self.chkIncludeNonLive = wx.CheckBox(
            parent=self.optionsPage,
            id=-1,
            label="Include non-live items",
            name="chkIncludeNonLive",
            style=0,
        )
        self.chkIncludeNonLive.SetValue(False)
        self.chkIncludeNonLive.SetToolTip(
            "Include non-live items in export (e.g. archived items)"
        )
        box.Add(self.chkIncludeNonLive, 1, wx.ALIGN_TOP | wx.ALL, padding)

        leftBox.Add(box)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.AddSpacer(indentWidth)
        label = wx.StaticText(
            self.optionsPage,
            -1,
            "Filename Conflicts:",
            size=(-1, -1),
            style=wx.ALIGN_RIGHT,
        )
        box.Add(label, 0, wx.ALIGN_TOP | wx.ALL, padding)
        self.cmbConflicts = wx.Choice(
            choices=[],
            id=-1,
            name="cmbConflicts",
            parent=self.optionsPage,
            size=wx.Size(250, 21),
            style=0,
        )
        box.Add(self.cmbConflicts, 1, wx.TOP | wx.ALL, padding)
        leftBox.Add(box, 0, wx.ALIGN_TOP | wx.ALL, padding)

        self.cmbConflicts.Append("Do not overwrite any files")
        self.cmbConflicts.Append("Overwrite files in target folder")
        self.cmbConflicts.Append("Overwrite files with same names")
        self.cmbConflicts.SetSelection(0)

        gridSizer.Add(leftBox, 0, wx.TOP | wx.ALL, padding)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.txtWhereClause = wx.TextCtrl(
            self.optionsPage, -1, "", size=wx.Size(420, 50), style=wx.TE_MULTILINE
        )
        font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, "Courier New")
        self.txtWhereClause.SetFont(font)
        box.Add(self.txtWhereClause, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        gridSizer.Add(box, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 0)

        self.optionsSizer.Add(gridSizer)

        line = wx.StaticLine(
            self.optionsPage, -1, size=(20, -1), style=wx.LI_HORIZONTAL
        )
        self.optionsSizer.Add(line, 0, wx.GROW | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)

        # options page Expert script buttons
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.optionsPage, -1, "Expert Scripts:", size=(-1, -1))
        box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, padding)
        self.optionsSizer.Add(box, 0, wx.ALL, 1)
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.btnStartScript = wx.Button(
            id=-1,
            label="Start Script",
            name="btnStartScript",
            parent=self.optionsPage,
            size=wx.Size(132, 23),
            style=0,
        )
        box.Add(self.btnStartScript, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.OnBtnStartScript, self.btnStartScript)
        self.btnPreScript = wx.Button(
            id=-1,
            label="Row Pre-Script",
            name="btnPreScript",
            parent=self.optionsPage,
            size=wx.Size(132, 23),
            style=0,
        )
        box.Add(self.btnPreScript, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.OnBtnPreScript, self.btnPreScript)
        self.btnPostScript = wx.Button(
            id=-1,
            label="Row Post-Script",
            name="btnPostScript",
            parent=self.optionsPage,
            size=wx.Size(132, 23),
            style=0,
        )
        box.Add(self.btnPostScript, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.OnBtnPostScript, self.btnPostScript)
        self.btnEndScript = wx.Button(
            id=-1,
            label="End Script",
            name="btnEndScript",
            parent=self.optionsPage,
            size=wx.Size(132, 23),
            style=0,
        )
        box.Add(self.btnEndScript, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.OnBtnEndScript, self.btnEndScript)
        self.optionsSizer.Add(box, 0, wx.ALL, 1)

        self.updateScriptButtonsLabels()

        # log page
        sizer = wx.BoxSizer(orient=wx.VERTICAL)

        box = wx.BoxSizer(orient=wx.HORIZONTAL)
        self.btnClearLog = wx.Button(
            id=-1, label="Clear", parent=self.logPage, size=wx.Size(90, 23), style=0
        )
        self.btnClearLog.SetToolTip("Clear log")
        self.btnClearLog.Bind(wx.EVT_BUTTON, self.OnBtnClearLog)
        box.Add(self.btnClearLog, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
        sizer.Add(box)

        sizer.Add(self.log, 1, wx.EXPAND)
        self.logPage.SetSizer(sizer)

        # import/export buttons
        width = 123
        height = 23
        left = 700
        top = 2
        gap = 2
        labelStart = "Start Import"
        labelTest = "Test Import"
        tooltopStart = "Perform an import/export into EQUELLA"
        tooltipTest = "Perform a test run (no items saved in EQUELLA)"

        self.btnConnStartImport = wx.Button(
            id=-1,
            label=labelStart,
            parent=self.connectionPage,
            pos=wx.Point(left + width + gap, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnConnStartImport.SetToolTip(tooltopStart)
        self.btnConnStartImport.Bind(wx.EVT_BUTTON, self.OnBtnStartImportButton)

        self.btnConnTestImport = wx.Button(
            id=-1,
            label=labelTest,
            parent=self.connectionPage,
            pos=wx.Point(left, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnConnTestImport.SetToolTip(tooltipTest)
        self.btnConnTestImport.Bind(wx.EVT_BUTTON, self.OnBtnTestImportButton)

        self.btnCsvStartImport = wx.Button(
            id=-1,
            label=labelStart,
            parent=self.csvPage,
            pos=wx.Point(left + width + gap, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnCsvStartImport.SetToolTip(tooltopStart)
        self.btnCsvStartImport.Bind(wx.EVT_BUTTON, self.OnBtnStartImportButton)

        self.btnCsvTestImport = wx.Button(
            id=-1,
            label=labelTest,
            parent=self.csvPage,
            pos=wx.Point(left, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnCsvTestImport.SetToolTip(tooltipTest)
        self.btnCsvTestImport.Bind(wx.EVT_BUTTON, self.OnBtnTestImportButton)

        self.btnOptionsStartImport = wx.Button(
            id=-1,
            label=labelStart,
            parent=self.optionsPage,
            pos=wx.Point(left + width + gap, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnOptionsStartImport.SetToolTip(tooltopStart)
        self.btnOptionsStartImport.Bind(wx.EVT_BUTTON, self.OnBtnStartImportButton)

        self.btnOptionsTestImport = wx.Button(
            id=-1,
            label=labelTest,
            parent=self.optionsPage,
            pos=wx.Point(left, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnOptionsTestImport.SetToolTip(tooltipTest)
        self.btnOptionsTestImport.Bind(wx.EVT_BUTTON, self.OnBtnTestImportButton)

        self.btnLogStartImport = wx.Button(
            id=-1,
            label=labelStart,
            parent=self.logPage,
            pos=wx.Point(left + width + gap, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnLogStartImport.SetToolTip(tooltopStart)
        self.btnLogStartImport.Bind(wx.EVT_BUTTON, self.OnBtnStartImportButton)

        self.btnLogTestImport = wx.Button(
            id=-1,
            label=labelTest,
            parent=self.logPage,
            pos=wx.Point(left, top),
            size=wx.Size(width, height),
            style=0,
        )
        self.btnLogTestImport.SetToolTip(tooltipTest)
        self.btnLogTestImport.Bind(wx.EVT_BUTTON, self.OnBtnTestImportButton)

        # toolbar and status bar
        self.mainStatusBar = wx.StatusBar(
            id=wxID_MAINFRAMEMAINSTATUSBAR, name="mainStatusBar", parent=self, style=0
        )
        self.mainStatusBar.SetToolTip("Status Bar")
        self._init_coll_mainStatusBar_Fields(self.mainStatusBar)

        self.mainToolbar = wx.ToolBar(
            id=wxID_MAINFRAMEMAINTOOLBAR,
            name="mainToolbar",
            parent=self,
            pos=wx.Point(0, 0),
            size=wx.Size(1006, 27),
            style=wx.TB_HORIZONTAL | wx.NO_BORDER,
        )

        self._init_coll_mainToolbar_Tools(self.mainToolbar)

        self.progressGauge = wx.Gauge(
            self.mainStatusBar, -1, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH
        )
        rect = self.mainStatusBar.GetFieldRect(1)
        self.progressGauge.SetPosition((rect.x, rect.y))
        self.progressGauge.SetSize((rect.width - 40, rect.height))

        # events to indicate that settings have been changed (and may need to be saved)
        self.Bind(wx.EVT_TEXT, self.OnInstitutionUrlChange, self.txtInstitutionUrl)
        self.Bind(wx.EVT_CHOICE, self.OnSettingChange, self.cmbEncoding)
        self.Bind(wx.EVT_TEXT, self.OnSettingChange, self.txtRowFilter)
        self.Bind(wx.EVT_TEXT, self.OnSettingChange, self.txtCSVPath)
        self.Bind(wx.EVT_TEXT, self.OnSettingChange, self.txtUsername)
        self.Bind(wx.EVT_TEXT, self.OnPasswordChange, self.txtPassword)
        self.Bind(wx.EVT_CHOICE, self.OnSettingChange, self.cmbCollections)
        self.columnsGrid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnSettingChange)
        self.Bind(wx.EVT_CHECKBOX, self.OnSettingChange, self.chkSaveAsDraft)
        self.Bind(wx.EVT_CHECKBOX, self.OnSettingChange, self.chkSaveTestXml)
        self.Bind(wx.EVT_CHOICE, self.OnSettingChange, self.cmbExistingMetadataMode)
        self.Bind(wx.EVT_CHECKBOX, self.OnSettingChange, self.chkAppendAttachments)
        self.Bind(wx.EVT_CHECKBOX, self.OnSettingChange, self.chkCreateNewVersions)
        self.Bind(wx.EVT_CHECKBOX, self.OnSettingChange, self.chkUseEBIUsername)
        self.Bind(
            wx.EVT_CHECKBOX,
            self.OnSettingChange,
            self.chkIgnoreNonexistentCollaborators,
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.OnSettingChange, self.chkSaveNonexistentUsernamesAsIDs
        )
        self.Bind(wx.EVT_CHECKBOX, self.OnExportChange, self.chkExport)
        self.Bind(wx.EVT_CHECKBOX, self.OnExportChange, self.chkIncludeNonLive)
        self.Bind(wx.EVT_CHOICE, self.OnSettingChange, self.cmbConflicts)
        self.Bind(wx.EVT_TEXT, self.OnSettingChange, self.txtWhereClause)
        self.Bind(wx.EVT_TEXT, self.OnSettingChange, self.txtAttachmentsBasepath)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # accelerator table for Save keyboard shortcuts
        randomCtrlSaveId = wx.NewId()
        randomCmdSaveId = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onCtrlS, id=randomCtrlSaveId)
        self.Bind(wx.EVT_MENU, self.onCtrlS, id=randomCmdSaveId)
        try:
            accel_tbl = wx.AcceleratorTable(
                [
                    (wx.ACCEL_CTRL, ord("S"), randomCtrlSaveId),
                    (wx.ACCEL_CMD, ord("S"), randomCmdSaveId),
                ]
            )
        except:
            accel_tbl = wx.AcceleratorTable(
                [(wx.ACCEL_CTRL, ord("S"), randomCtrlSaveId)]
            )
        self.SetAcceleratorTable(accel_tbl)

        self._init_sizers()
        self.txtInstitutionUrl.SetFocus()

    def OnSettingChange(self, event):
        self.dirtyUI = True
        event.Skip()

    def OnPasswordChange(self, event):
        if self.savePassword:
            self.dirtyUI = True
            event.Skip()

    def OnExportChange(self, event):
        self.UpdateImportExportButtons()
        self.dirtyUI = True
        event.Skip()

    def OnInstitutionUrlChange(self, event):
        if self.engine is not None:
            self.engine.collectionIDs.clear()
            self.engine.eqVersionmm = ""
            self.engine.eqVersionmmr = ""
            self.engine.eqVersionDisplay = ""
            self.dirtyUI = True
        event.Skip()

    def UpdateImportExportButtons(self):
        if self.chkExport.GetValue():
            self.btnConnStartImport.SetLabel("Start Export")
            self.btnConnTestImport.SetLabel("Test Export")
            self.btnCsvStartImport.SetLabel("Start Export")
            self.btnCsvTestImport.SetLabel("Test Export")
            self.btnOptionsStartImport.SetLabel("Start Export")
            self.btnOptionsTestImport.SetLabel("Test Export")
            self.btnLogStartImport.SetLabel("Start Export")
            self.btnLogTestImport.SetLabel("Test Export")
        else:
            self.btnConnStartImport.SetLabel("Start Import")
            self.btnConnTestImport.SetLabel("Test Import")
            self.btnCsvStartImport.SetLabel("Start Import")
            self.btnCsvTestImport.SetLabel("Test Import")
            self.btnOptionsStartImport.SetLabel("Start Import")
            self.btnOptionsTestImport.SetLabel("Test Import")
            self.btnLogStartImport.SetLabel("Start Import")
            self.btnLogTestImport.SetLabel("Test Import")

    def onCtrlS(self, event):
        self.mainStatusBar.SetStatusText("Saving...", 0)
        self.saveSettings(True)
        wx.GetApp().Yield()
        self.mainStatusBar.SetStatusText("Ready", 0)

    def getCSVPath(self):
        return os.path.join(
            os.path.dirname(self.settingsfile), self.txtCSVPath.GetValue()
        )

    def OnBtnBrowseBasePath(self, evt):
        dlg = wx.DirDialog(
            self, "Choose a folder/directory:", style=wx.DD_DEFAULT_STYLE
        )

        # set the default directory for the dialog
        dlg.SetPath(
            os.path.join(
                os.path.dirname(self.getCSVPath()),
                self.txtAttachmentsBasepath.GetValue().strip(),
            )
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.txtAttachmentsBasepath.SetValue(dlg.GetPath())

        # Only destroy a dialog after you're done with it.
        dlg.Destroy()

    def OnBtnStartScript(self, evt):
        wrapper = [self.startScript]
        self.openScriptEditor(wrapper, "Start Script")
        self.startScript = wrapper[0]
        self.updateScriptButtonsLabels()

    def OnBtnEndScript(self, evt):
        wrapper = [self.endScript]
        self.openScriptEditor(wrapper, "End Script")
        self.endScript = wrapper[0]
        self.updateScriptButtonsLabels()

    def OnBtnPreScript(self, evt):
        wrapper = [self.preScript]
        self.openScriptEditor(wrapper, "Row Pre-Script")
        self.preScript = wrapper[0]
        self.updateScriptButtonsLabels()

    def OnBtnPostScript(self, evt):
        wrapper = [self.postScript]
        self.openScriptEditor(wrapper, "Row Post-Script")
        self.postScript = wrapper[0]
        self.updateScriptButtonsLabels()

    def openScriptEditor(self, script, title):
        dlgScript = ScriptDialog(self)

        # get last used dimensions
        try:
            if self.config.has_option("State", "scriptdialogsize"):
                rawsize = self.config.get("State", "scriptdialogsize")
                size = tuple(int(v) for v in re.findall("[0-9]+", rawsize))
                dlgScript.SetSize(size)

        except:
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.engine.echo(
                    "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    ),
                    log=False,
                    style=2,
                )

        dlgScript.CenterOnScreen()
        dlgScript.SetTitle(title)
        dlgScript.scriptEditor.SetText(script[0])
        dlgScript.scriptEditor.EmptyUndoBuffer()
        val = dlgScript.ShowModal()
        if val == wx.ID_OK:
            script[0] = dlgScript.scriptEditor.GetText().replace("\r\n", "\n")
            self.dirtyUI = True

        # save dimensions
        try:
            if not "State" in self.config.sections():
                self.parent.config.add_section("State")
            self.config.set("State", "scriptdialogsize", str(dlgScript.GetSize()))
            self.config.write(open(self.propertiesFile, "w"))
        except:
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.engine.echo(
                    "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    ),
                    log=False,
                    style=2,
                )

        dlgScript.Destroy()

    def updateScriptButtonsLabels(self):
        if self.startScript.strip() != "":
            self.btnStartScript.SetLabel("Start Script*")
        else:
            self.btnStartScript.SetLabel("Start Script")
        if self.endScript.strip() != "":
            self.btnEndScript.SetLabel("End Script*")
        else:
            self.btnEndScript.SetLabel("End Script")
        if self.preScript.strip() != "":
            self.btnPreScript.SetLabel("Row Pre-Script*")
        else:
            self.btnPreScript.SetLabel("Row Pre-Script")
        if self.postScript.strip() != "":
            self.btnPostScript.SetLabel("Row Post-Script*")
        else:
            self.btnPostScript.SetLabel("Row Post-Script")

    def OnBtnClearLog(self, event):
        self.ClearLog()

    def ClearLog(self):
        self.log.SetReadOnly(False)
        self.log.ClearAll()
        self.log.AddLogText(self.engine.welcomeLine1 + "\n", 1)
        self.log.AddLogText(self.engine.welcomeLine2 + "\n", 1)

    def __init__(self, parent):
        # constants
        self.METADATA = Constants.METADATA
        self.ATTACHMENTLOCATIONS = Constants.ATTACHMENTLOCATIONS
        self.ATTACHMENTNAMES = Constants.ATTACHMENTNAMES
        self.CUSTOMATTACHMENTS = Constants.CUSTOMATTACHMENTS
        self.RAWFILES = Constants.RAWFILES
        self.URLS = Constants.URLS
        self.HYPERLINKNAMES = Constants.HYPERLINKNAMES
        self.EQUELLARESOURCES = Constants.EQUELLARESOURCES
        self.EQUELLARESOURCENAMES = Constants.EQUELLARESOURCENAMES
        self.COMMANDS = Constants.COMMANDS
        self.TARGETIDENTIFIER = Constants.TARGETIDENTIFIER
        self.TARGETVERSION = Constants.TARGETVERSION
        self.COLLECTION = Constants.COLLECTION
        self.OWNER = Constants.OWNER
        self.COLLABORATORS = Constants.COLLABORATORS
        self.ITEMID = Constants.ITEMID
        self.ITEMVERSION = Constants.ITEMVERSION
        self.THUMBNAILS = Constants.THUMBNAILS
        self.SELECTEDTHUMBNAIL = Constants.SELECTEDTHUMBNAIL
        self.ROWERROR = Constants.ROWERROR
        self.IGNORE = Constants.IGNORE

        self.COLUMN_POS = Constants.COLUMN_POS
        self.COLUMN_HEADING = Constants.COLUMN_HEADING
        self.COLUMN_DATATYPE = Constants.COLUMN_DATATYPE
        self.COLUMN_DISPLAY = Constants.COLUMN_DISPLAY
        self.COLUMN_SOURCEIDENTIFIER = Constants.COLUMN_SOURCEIDENTIFIER
        self.COLUMN_XMLFRAGMENT = Constants.COLUMN_XMLFRAGMENT
        self.COLUMN_DELIMITER = Constants.COLUMN_DELIMITER

        self.OVERWRITENONE = Constants.OVERWRITENONE
        self.OVERWRITEEXISTING = Constants.OVERWRITEEXISTING
        self.OVERWRITEALL = Constants.OVERWRITEALL

        # globals
        self.version = ""
        self.debug = False
        self.license = ""
        self.copyright = ""
        self.dirtyUI = False
        self.encodingOptions = ["utf-8", "latin1"]
        self.startScript = ""
        self.endScript = ""
        self.preScript = ""
        self.postScript = ""
        self.clearLogEachRun = False
        self.savePassword = True
        self.settingsfile = ""

        # Initialize SettingsManager early so it's available for pre-fill
        self.settingsManager = SettingsManager()

        self._init_ctrls(parent)

        rect = self.mainStatusBar.GetFieldRect(1)
        self.progressGauge.SetPosition((rect.x, rect.y))
        self.progressBarWidth = rect.width - 40
        self.progressBarHeight = rect.height
        self.progressGauge.SetSize((0, self.progressBarHeight))

        self.Center()

        iconFile = os.path.join(self.scriptFolder, "ebibig.ico")
        icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        # create grid and set column widths and headings
        self.columnsGrid.CreateGrid(0, 7)

        self.columnsGrid.SetRowLabelSize(0)

        self.columnsGrid.SetColLabelValue(0, self.COLUMN_POS)
        self.columnsGrid.SetColSize(0, 60)

        self.columnsGrid.SetColLabelValue(1, self.COLUMN_HEADING)
        self.columnsGrid.SetColSize(1, 360)

        self.columnsGrid.SetColLabelValue(2, self.COLUMN_DATATYPE)
        self.columnsGrid.SetColSize(2, 180)

        self.columnsGrid.SetColLabelValue(3, self.COLUMN_DISPLAY)
        self.columnsGrid.SetColSize(3, 60)

        self.columnsGrid.SetColLabelValue(4, self.COLUMN_SOURCEIDENTIFIER)
        self.columnsGrid.SetColSize(4, 120)

        self.columnsGrid.SetColLabelValue(5, self.COLUMN_XMLFRAGMENT)
        self.columnsGrid.SetColSize(5, 110)

        self.columnsGrid.SetColLabelValue(6, self.COLUMN_DELIMITER)
        self.columnsGrid.SetColSize(6, 80)

        # data structures to store column settings
        self.currentColumns = []
        self.currentColumnHeadings = []

        # mouse cursors
        self.normalCursor = wx.Cursor(wx.CURSOR_ARROW)
        self.waitCursor = wx.Cursor(wx.CURSOR_WAIT)

        # main ebi engine
        self.engine = None

        self.settingsFile = ""
        self.EBIDownloadPage = ""

        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSTOP, False)
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARPAUSE, False)

        self.config = configparser.ConfigParser()

        # Pre-fill connection settings from saved preferences at startup
        saved_url = self.settingsManager.get("institution_url", "")
        if saved_url:
            self.txtInstitutionUrl.SetValue(saved_url)

        saved_username = self.settingsManager.get("username", "")
        if saved_username:
            self.txtUsername.SetValue(saved_username)

        saved_password = self.settingsManager.get("password", "")
        if saved_password:
            self.txtPassword.SetValue(saved_password)

        saved_client_id = self.settingsManager.get("oauth_client_id", "")
        if saved_client_id:
            self.txtOAuthClientId.SetValue(saved_client_id)

    def createEngine(
        self, version, copyright, license, EBIDownloadPage, propertiesFile
    ):
        self.version = version
        self.copyright = copyright
        self.license = license
        self.EBIDownloadPage = EBIDownloadPage
        self.propertiesFile = propertiesFile

        # SettingsManager already created in __init__, just use it
        self.engine = Engine.Engine(self, self.version, self.copyright)
        self.engine.setLog(self.log)

        # Pass SettingsManager to engine
        self.engine.settingsManager = self.settingsManager

        manualConfigPrinted = False
        try:
            self.config.read(self.propertiesFile)
            try:
                if self.config.has_option("State", "mainframesize"):
                    size = self.config.get("State", "mainframesize")
                    self.SetClientSize(
                        tuple(int(v) for v in re.findall("[0-9]+", size))
                    )
                    self.Center()
            except:
                pass

            try:
                if self.config.has_option("Configuration", "attachmentmetadatatargets"):
                    self.engine.attachmentMetadataTargets = self.config.getboolean(
                        "Configuration", "attachmentmetadatatargets"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'attachmentmetadatatargets' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "attachmentchunksize"):
                    self.engine.chunkSize = self.config.getint(
                        "Configuration", "attachmentchunksize"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'attachmentchunksize' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "networklogging"):
                    self.engine.networkLogging = self.config.getboolean(
                        "Configuration", "networklogging"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'networklogging' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "proxyaddress"):
                    self.engine.proxy = self.config.get("Configuration", "proxyaddress")
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'proxyaddress': "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "proxyusername"):
                    self.engine.proxyUsername = self.config.get(
                        "Configuration", "proxyusername"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'proxyusername': "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "proxypassword"):
                    if self.config.get("Configuration", "proxypassword") != "":
                        self.engine.proxyPassword = self.dc(
                            self.config.get("Configuration", "proxypassword")
                        )
                    else:
                        self.engine.proxyPassword = ""
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'proxyusername': "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "scormformatsupport"):
                    self.engine.scormformatsupport = self.config.getboolean(
                        "Configuration", "scormformatsupport"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'scormformatsupport' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "clearlogeachrun"):
                    self.clearLogEachRun = self.config.getboolean(
                        "Configuration", "clearlogeachrun"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'clearlogonrun' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "savepassword"):
                    self.savePassword = self.config.getboolean(
                        "Configuration", "savepassword"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'savepassword' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )
            try:
                if self.config.has_option("Configuration", "logbuffersize"):
                    self.log.logBufferSize = self.config.getint(
                        "Configuration", "logbuffersize"
                    )
            except:
                manualConfigPrinted = True
                self.engine.echo(
                    "Unable to read properties file value 'logbuffersize' (reverting to default value): "
                    + str(sys.exc_info()[1])
                )

        except:
            self.engine.echo(
                "Unable to read properties file (reverting to default values): "
                + str(sys.exc_info()[1])
            )
            manualConfigPrinted = True

        if manualConfigPrinted and not self.debug:
            self.engine.echo("")

    def printNonDefaultPreferences(self):
        manualConfigPrinted = False
        if self.debug:
            self.engine.echo("debug = True")
            manualConfigPrinted = True
        if not self.engine.attachmentMetadataTargets:
            self.engine.echo(
                "attachmentmetadatatargets = "
                + str(self.engine.attachmentMetadataTargets)
            )
            manualConfigPrinted = True
        if self.engine.chunkSize != self.engine.defaultChunkSize:
            self.engine.echo("attachmentchunksize = " + str(self.engine.chunkSize))
            manualConfigPrinted = True
        if self.engine.networkLogging:
            self.engine.echo("networklogging = " + str(self.engine.networkLogging))
            manualConfigPrinted = True
        if not self.engine.scormformatsupport:
            self.engine.echo(
                "scormformatsupport = " + str(self.engine.scormformatsupport)
            )
            manualConfigPrinted = True
        if manualConfigPrinted:
            self.engine.echo("")

    def setVersion(self, version):
        self.version = version

    def setDebug(self, debug):
        self.debug = debug

        if not self.debug:
            try:
                self.config.read(self.propertiesFile)
                self.debug = self.config.getboolean("Configuration", "Debug")
            except:
                if self.debug:
                    print((str(sys.exc_info()[1])))

        self.engine.setDebug(self.debug)
        if self.debug:
            self.engine.echo("self.scriptFolder = %s\n" % self.scriptFolder, log=False)

    def OnMainFrameActivate(self, event):
        pass

    def loadCurrentSettings(self):
        # connection settings
        self.engine.institutionUrl = self.txtInstitutionUrl.GetValue()
        if self.txtInstitutionUrl.GetValue().endswith("/"):
            self.engine.institutionUrl = self.txtInstitutionUrl.GetValue()[:-1]
        self.engine.username = self.txtUsername.GetValue()
        self.engine.password = self.txtPassword.GetValue()
        self.engine.oauthClientId = self.txtOAuthClientId.GetValue()
        self.engine.collection = self.cmbCollections.GetStringSelection()
        self.engine.csvFilePath = self.getCSVPath()
        self.engine.encoding = self.cmbEncoding.GetStringSelection()
        self.engine.rowFilter = self.txtRowFilter.GetValue()

        # options
        self.engine.saveAsDraft = self.chkSaveAsDraft.GetValue()
        self.engine.saveTestXML = self.chkSaveTestXml.GetValue()
        self.engine.existingMetadataMode = self.cmbExistingMetadataMode.GetSelection()
        self.engine.appendAttachments = self.chkAppendAttachments.GetValue()
        self.engine.createNewVersions = self.chkCreateNewVersions.GetValue()
        self.engine.useEBIUsername = self.chkUseEBIUsername.GetValue()
        self.engine.ignoreNonexistentCollaborators = (
            self.chkIgnoreNonexistentCollaborators.GetValue()
        )
        self.engine.saveNonexistentUsernamesAsIDs = (
            self.chkSaveNonexistentUsernamesAsIDs.GetValue()
        )
        self.engine.attachmentsBasepath = self.txtAttachmentsBasepath.GetValue()
        self.engine.export = self.chkExport.GetValue()
        self.engine.includeNonLive = self.chkIncludeNonLive.GetValue()
        self.engine.overwriteMode = self.cmbConflicts.GetSelection()
        self.engine.whereClause = self.txtWhereClause.GetValue()
        self.engine.startScript = self.startScript
        self.engine.endScript = self.endScript
        self.engine.preScript = self.preScript
        self.engine.postScript = self.postScript

        self.MemorizeColumnSettings()
        self.engine.currentColumns = self.currentColumns
        self.engine.columnHeadings = self.currentColumnHeadings

    def OnBtnBrowseCSVButton(self, event):
        try:
            wildcard = "Comma Seperated View (*.csv)|*.csv|All files (*.*)|*.*"

            dlg = wx.FileDialog(
                self,
                message="Select a CSV",
                defaultDir=os.getcwd(),
                defaultFile="",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_CHANGE_DIR,
            )

            if dlg.ShowModal() == wx.ID_OK:
                paths = dlg.GetPaths()

                self.txtCSVPath.SetValue(paths[0])
                self.LoadCSV()

            dlg.Destroy()
        except:
            self.SetCursor(self.normalCursor)
            self.mainStatusBar.SetStatusText("Error loading CSV", 0)

            errorMessage = self.engine.translateError(str(sys.exc_info()[1]))

            dlg = wx.MessageDialog(
                None,
                "Error loading CSV:\n\n" + errorMessage,
                "CSV Load Error",
                wx.OK | wx.ICON_ERROR,
            )
            dlg.ShowModal()
            dlg.Destroy()

            self.mainStatusBar.SetStatusText("Ready", 0)

    def LoadCSV(self):
        self.mainStatusBar.SetStatusText("Loading CSV...", 0)

        encoding = self.cmbEncoding.GetStringSelection()
        if encoding.lower() == "utf-8":
            encoding = "utf-8-sig"
        reader = csv.reader(open(self.getCSVPath(), "r", encoding=encoding, newline=""))

        # store the rows of the CSV in an array
        csvArray = []
        for row in reader:
            csvArray.append(row)

        self.LoadColumns(csvArray)
        plural = ""
        if len(csvArray) - 1 != 1:
            plural = "s"
        self.mainStatusBar.SetStatusText(
            "CSV loaded: %s record%s" % (len(csvArray) - 1, plural), 0
        )

    def verifyCurrentColumnsMatchCSV(self):
        if self.txtCSVPath.GetValue() != "" and not os.path.isdir(
            self.txtCSVPath.GetValue()
        ):
            encoding = self.cmbEncoding.GetStringSelection()
            if encoding.lower() == "utf-8":
                encoding = "utf-8-sig"
            reader = csv.reader(
                open(self.getCSVPath(), "r", encoding=encoding, newline="")
            )

            # store the first row of the CSV in an array
            csvHeadings = []
            for row in reader:
                csvHeadings = row
                break

            # check if same number of grid headings as there are CSV headings
            if len(csvHeadings) != self.columnsGrid.GetNumberRows():
                return False

            # check if all CSV headings match grid headings
            i = 0
            for columnHeading in csvHeadings:
                if columnHeading.strip() != self.columnsGrid.GetCellValue(i, 1).strip():
                    return False
                i += 1

        return True

    def OnBtnReloadCSVButton(self, event):
        try:
            result = wx.ID_YES
            columnsAlreadyMatch = self.verifyCurrentColumnsMatchCSV()
            if not columnsAlreadyMatch and self.columnsGrid.GetNumberRows() != 0:
                dlg = wx.MessageDialog(
                    None,
                    "CSV headings do not match the current settings.\n\nLoad the CSV and update the current settings?",
                    "CSV Load",
                    wx.YES_NO | wx.ICON_EXCLAMATION,
                )
                result = dlg.ShowModal()
                dlg.Destroy()
            if result == wx.ID_YES:
                self.SetCursor(self.waitCursor)
                self.LoadCSV()
                self.SetCursor(self.normalCursor)
            if columnsAlreadyMatch:
                dlg = wx.MessageDialog(
                    None,
                    "Columns settings correctly match CSV column headings",
                    "CSV Load",
                    wx.OK | wx.ICON_INFORMATION,
                )
                dlg.ShowModal()
                dlg.Destroy()

        except:
            self.SetCursor(self.normalCursor)
            self.mainStatusBar.SetStatusText("Error loading CSV", 0)

            errorMessage = self.engine.translateError(str(sys.exc_info()[1]))

            dlg = wx.MessageDialog(
                None,
                "Error loading CSV:\n\n" + errorMessage,
                "CSV Load Error",
                wx.OK | wx.ICON_ERROR,
            )
            dlg.ShowModal()
            dlg.Destroy()

            self.mainStatusBar.SetStatusText("Ready", 0)

    def MemorizeColumnSettings(self):
        self.currentColumnHeadings = []
        self.currentColumns = []

        self.currentColumnDataType = {}
        self.currentDisplay = {}
        self.currentSourceIdentifier = {}
        self.currentXMLFragment = {}
        self.currentDelimiter = {}
        for row in range(0, self.columnsGrid.GetNumberRows()):
            columnHeading = self.columnsGrid.GetCellValue(row, 1)
            self.currentColumnHeadings.append(columnHeading)

            columnSettings = {}
            columnSettings[self.COLUMN_HEADING] = self.columnsGrid.GetCellValue(row, 1)
            columnSettings[self.COLUMN_DATATYPE] = self.columnsGrid.GetCellValue(row, 2)
            columnSettings[self.COLUMN_DISPLAY] = self.columnsGrid.GetCellValue(row, 3)
            columnSettings[self.COLUMN_SOURCEIDENTIFIER] = (
                self.columnsGrid.GetCellValue(row, 4)
            )
            columnSettings[self.COLUMN_XMLFRAGMENT] = self.columnsGrid.GetCellValue(
                row, 5
            )
            columnSettings[self.COLUMN_DELIMITER] = self.columnsGrid.GetCellValue(
                row, 6
            )
            self.currentColumns.append(columnSettings)

    def GetExcelColumnName(self, columnNumber):
        dividend = columnNumber
        columnName = ""
        while dividend > 0:
            modulo = (dividend - 1) % 26
            columnName = chr(65 + modulo) + columnName
            dividend = (dividend - modulo) // 26

        return columnName

    def LoadColumns(self, csvArray):
        self.MemorizeColumnSettings()

        # Delete all grid rows
        if self.columnsGrid.GetNumberRows() > 0:
            self.columnsGrid.DeleteRows(0, self.columnsGrid.GetNumberRows())

        # iterate through columns in CSV
        row = 0
        for csvColumnHeadingUnstripped in csvArray[0]:

            # strip the column heading of leading and trailing whitespace
            csvColumnHeading = csvColumnHeadingUnstripped.strip()

            colPos = str(row + 1) + "- " + self.GetExcelColumnName(row + 1)

            self.columnsGrid.AppendRows()
            self.columnsGrid.SetCellValue(row, 0, colPos)
            self.columnsGrid.SetCellValue(row, 1, csvColumnHeading)

            # check if columns already loaded and determine it's occurence if so (may be more than one)
            columnPositionLoaded = -1
            occurenceInCsv = csvArray[0][: row + 1].count(csvColumnHeadingUnstripped)
            for idx, col in enumerate(self.currentColumnHeadings):
                occurenceInCurrentColumns = self.currentColumnHeadings[: idx + 1].count(
                    csvColumnHeading
                )
                if (
                    col == csvColumnHeading
                    and occurenceInCurrentColumns == occurenceInCsv
                ):
                    columnPositionLoaded = idx

            if columnPositionLoaded != -1:
                # column already loaded so update with current settings (of same occurence if more than one)
                self.columnsGrid.SetCellValue(
                    row,
                    2,
                    self.currentColumns[columnPositionLoaded][self.COLUMN_DATATYPE],
                )
                self.columnsGrid.SetCellValue(
                    row,
                    3,
                    self.currentColumns[columnPositionLoaded][self.COLUMN_DISPLAY],
                )
                self.columnsGrid.SetCellValue(
                    row,
                    4,
                    self.currentColumns[columnPositionLoaded][
                        self.COLUMN_SOURCEIDENTIFIER
                    ],
                )
                self.columnsGrid.SetCellValue(
                    row,
                    5,
                    self.currentColumns[columnPositionLoaded][self.COLUMN_XMLFRAGMENT],
                )
                self.columnsGrid.SetCellValue(
                    row,
                    6,
                    self.currentColumns[columnPositionLoaded][self.COLUMN_DELIMITER],
                )
            else:
                # column not loaded so add to grid as metadata datatype
                self.columnsGrid.SetCellValue(row, 2, self.METADATA)

            # set first two cells of each row read-only
            self.columnsGrid.SetReadOnly(row, 0)
            self.columnsGrid.SetReadOnly(row, 1)

            # set cell alignment
            self.columnsGrid.SetCellAlignment(row, 3, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            self.columnsGrid.SetCellAlignment(row, 4, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            self.columnsGrid.SetCellAlignment(row, 5, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            self.columnsGrid.SetCellAlignment(row, 6, wx.ALIGN_CENTER, wx.ALIGN_CENTER)

            # set cell editors (drop-downs)
            # Use grid attributes to manage editors safely
            attr2 = wx.grid.GridCellAttr()
            attr2.SetEditor(
                wx.grid.GridCellChoiceEditor(
                    [
                        self.METADATA,
                        self.ATTACHMENTLOCATIONS,
                        self.ATTACHMENTNAMES,
                        self.CUSTOMATTACHMENTS,
                        self.RAWFILES,
                        self.URLS,
                        self.HYPERLINKNAMES,
                        self.EQUELLARESOURCES,
                        self.EQUELLARESOURCENAMES,
                        self.COMMANDS,
                        self.TARGETIDENTIFIER,
                        self.TARGETVERSION,
                        self.COLLECTION,
                        self.OWNER,
                        self.COLLABORATORS,
                        self.ITEMID,
                        self.ITEMVERSION,
                        self.THUMBNAILS,
                        self.SELECTEDTHUMBNAIL,
                        self.ROWERROR,
                        self.IGNORE,
                    ],
                    False,
                )
            )
            self.columnsGrid.SetAttr(row, 2, attr2)

            # Boolean editors for columns 3, 4, 5
            attr3 = wx.grid.GridCellAttr()
            boolEditor3 = wx.grid.GridCellBoolEditor()
            try:
                boolEditor3.UseStringValues("YES", "")
            except:
                pass
            attr3.SetEditor(boolEditor3)
            self.columnsGrid.SetAttr(row, 3, attr3)

            attr4 = wx.grid.GridCellAttr()
            boolEditor4 = wx.grid.GridCellBoolEditor()
            try:
                boolEditor4.UseStringValues("YES", "")
            except:
                pass
            attr4.SetEditor(boolEditor4)
            self.columnsGrid.SetAttr(row, 4, attr4)

            attr5 = wx.grid.GridCellAttr()
            boolEditor5 = wx.grid.GridCellBoolEditor()
            try:
                boolEditor5.UseStringValues("YES", "")
            except:
                pass
            attr5.SetEditor(boolEditor5)
            self.columnsGrid.SetAttr(row, 5, attr5)

            self.setCellStates(row)

            row += 1

    def OnMainToolbarSaveTool(self, event):
        event.Skip()

    # sets cell readonly or editable and sets the background color accordingly
    def setCellReadOnly(self, row, col, readonly=True, clearvalue=True):
        if readonly:
            if clearvalue:
                self.columnsGrid.SetCellValue(row, col, "")
            self.columnsGrid.SetReadOnly(row, col)
            self.columnsGrid.SetCellBackgroundColour(row, col, wx.Colour(230, 230, 240))
        else:
            self.columnsGrid.SetReadOnly(row, col, False)
            self.columnsGrid.SetCellBackgroundColour(row, col, wx.NullColour)

    # set the grid cell states of a row based on the Column Data Type
    def setCellStates(self, row):
        if self.columnsGrid.GetCellValue(row, 2) == self.IGNORE:
            self.setCellReadOnly(row, 3, False)
            self.setCellReadOnly(row, 4, True, False)
            self.setCellReadOnly(row, 5, True, False)
            self.setCellReadOnly(row, 6, True, False)
        else:
            if self.columnsGrid.GetCellValue(row, 2) == self.METADATA:
                # make all the cells editable
                self.setCellReadOnly(row, 3, False)
                self.setCellReadOnly(row, 4, False)
                self.setCellReadOnly(row, 5, False)
                self.setCellReadOnly(row, 6, False)
            else:
                self.setCellReadOnly(row, 4)
                self.setCellReadOnly(row, 5)

            # make Delimiter editable for the following column datatypes
            if (
                self.columnsGrid.GetCellValue(row, 2)
                in [
                    self.METADATA,
                    self.ATTACHMENTLOCATIONS,
                    self.ATTACHMENTNAMES,
                    self.RAWFILES,
                    self.URLS,
                    self.HYPERLINKNAMES,
                    self.EQUELLARESOURCES,
                    self.EQUELLARESOURCENAMES,
                    self.THUMBNAILS,
                    self.COLLABORATORS,
                ]
                and self.columnsGrid.GetCellValue(row, 5) != "YES"
            ):

                self.setCellReadOnly(row, 6, False)
            else:
                self.setCellReadOnly(row, 6)

            # make Display editable for the following column datatypes
            if self.columnsGrid.GetCellValue(row, 2) in [self.METADATA, self.IGNORE]:
                self.setCellReadOnly(row, 3, False)
            else:
                self.setCellReadOnly(row, 3)

    def OnColumnsGridGridCellChange(self, event):
        row = event.GetRow()
        col = event.GetCol()

        # check if Column Data Type has been changed
        if col in [2, 5]:

            self.setCellStates(row)

            # check for any columns Data types that should only have one column selected
            if self.columnsGrid.GetCellValue(row, col) in [
                self.TARGETIDENTIFIER,
                self.TARGETVERSION,
                self.ITEMID,
                self.ITEMVERSION,
                self.THUMBNAILS,
                self.SELECTEDTHUMBNAIL,
                self.ROWERROR,
                self.COMMANDS,
                self.COLLECTION,
                self.OWNER,
                self.COLLECTION,
                self.COLLABORATORS,
            ]:

                for i in range(0, self.columnsGrid.GetNumberRows()):
                    if i != row and self.columnsGrid.GetCellValue(
                        i, col
                    ) == self.columnsGrid.GetCellValue(row, col):
                        # set any other duplicate settings to Metadata
                        self.columnsGrid.SetCellValue(i, col, self.METADATA)
                        self.setCellReadOnly(i, 3, False)
                        self.setCellReadOnly(i, 4, False)
                        self.setCellReadOnly(i, 5, False)
                        self.setCellReadOnly(i, 6, False)

        # make certain only one column has Source Identifier checked
        if col == 4:
            for i in range(0, self.columnsGrid.GetNumberRows()):
                if i != row:
                    self.columnsGrid.SetCellValue(i, col, "")

    def ec(self, message):
        cm = ""
        for i in range(0, len(message)):
            cm = cm + "%(#)03d" % {"#": ord(message[i]) - i - 1}
        if len(message) < 25:
            cm = cm + random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            for i in range(0, 24 - len(message)):
                cm = cm + random.choice("01234567890ABCDEF")
        return cm

    def dc(self, cm):
        message = ""
        i = 0
        while i < len(cm):
            try:
                message = message + chr(int(cm[i : i + 3]) + i // 3 + 1)
            except:
                break
            i = i + 3
        return message

    def saveSettings(self, overwrite=False):
        self.SetCursor(self.waitCursor)

        # load column settings to memory
        self.MemorizeColumnSettings()

        # create xml document
        settingsDoc = Document()
        rootNode = settingsDoc.createElement("ebi_settings")
        settingsDoc.appendChild(rootNode)

        # create and populate CSV and connection fields
        institutionUrlNode = settingsDoc.createElement("institution_url")
        if self.txtInstitutionUrl.GetValue().strip() != "":
            institutionUrlNode.appendChild(
                settingsDoc.createTextNode(self.txtInstitutionUrl.GetValue())
            )
        rootNode.appendChild(institutionUrlNode)

        usernameNode = settingsDoc.createElement("username")
        if self.txtUsername.GetValue().strip() != "":
            usernameNode.appendChild(
                settingsDoc.createTextNode(self.txtUsername.GetValue())
            )
        rootNode.appendChild(usernameNode)

        if self.savePassword:
            passwordNode = settingsDoc.createElement("password")
            passwordNode.appendChild(
                settingsDoc.createTextNode(self.ec(self.txtPassword.GetValue()))
            )
            rootNode.appendChild(passwordNode)

        collectionNode = settingsDoc.createElement("collection")
        if self.cmbCollections.GetStringSelection() != "":
            collectionNode.appendChild(
                settingsDoc.createTextNode(self.cmbCollections.GetStringSelection())
            )
        rootNode.appendChild(collectionNode)

        csvNode = settingsDoc.createElement("csv_location")
        if self.txtCSVPath.GetValue().strip() != "":
            csvNode.appendChild(settingsDoc.createTextNode(self.txtCSVPath.GetValue()))
        rootNode.appendChild(csvNode)

        rowFilterNode = settingsDoc.createElement("row_filter")
        if self.txtRowFilter.GetValue().strip() != "":
            rowFilterNode.appendChild(
                settingsDoc.createTextNode(self.txtRowFilter.GetValue())
            )
        rootNode.appendChild(rowFilterNode)

        csvEncodingNode = settingsDoc.createElement("csv_encoding")
        csvEncodingNode.appendChild(
            settingsDoc.createTextNode(self.cmbEncoding.GetStringSelection())
        )
        rootNode.appendChild(csvEncodingNode)

        # create and populate columns node
        columnsNode = settingsDoc.createElement("columns")
        rootNode.appendChild(columnsNode)
        for colIndex, csvColumnHeading in enumerate(self.currentColumnHeadings):
            columnNode = settingsDoc.createElement("column")

            headingNode = settingsDoc.createElement("heading")
            headingNode.appendChild(settingsDoc.createTextNode(csvColumnHeading))
            columnNode.appendChild(headingNode)

            columnDataTypeNode = settingsDoc.createElement("column_data_type")
            columnDataTypeNode.appendChild(
                settingsDoc.createTextNode(
                    self.currentColumns[colIndex][self.COLUMN_DATATYPE]
                )
            )
            columnNode.appendChild(columnDataTypeNode)

            displayNode = settingsDoc.createElement("display")
            if self.currentColumns[colIndex][self.COLUMN_DISPLAY].strip() != "":
                displayNode.appendChild(
                    settingsDoc.createTextNode(
                        self.currentColumns[colIndex][self.COLUMN_DISPLAY]
                    )
                )
            columnNode.appendChild(displayNode)

            sourceIdentifierNode = settingsDoc.createElement("source_identifier")
            if (
                self.currentColumns[colIndex][self.COLUMN_SOURCEIDENTIFIER].strip()
                != ""
            ):
                sourceIdentifierNode.appendChild(
                    settingsDoc.createTextNode(
                        self.currentColumns[colIndex][self.COLUMN_SOURCEIDENTIFIER]
                    )
                )
            columnNode.appendChild(sourceIdentifierNode)

            xmlFragmentNode = settingsDoc.createElement("xml_fragment")
            if self.currentColumns[colIndex][self.COLUMN_XMLFRAGMENT].strip() != "":
                xmlFragmentNode.appendChild(
                    settingsDoc.createTextNode(
                        self.currentColumns[colIndex][self.COLUMN_XMLFRAGMENT]
                    )
                )
            columnNode.appendChild(xmlFragmentNode)

            delimiterNode = settingsDoc.createElement("delimiter")
            if self.currentColumns[colIndex][self.COLUMN_DELIMITER].strip() != "":
                delimiterNode.appendChild(
                    settingsDoc.createTextNode(
                        self.currentColumns[colIndex][self.COLUMN_DELIMITER]
                    )
                )
            columnNode.appendChild(delimiterNode)

            columnsNode.appendChild(columnNode)

        # save Options to xml
        saveAsDraftNode = settingsDoc.createElement("save_as_draft")
        if self.chkSaveAsDraft.GetValue():
            saveAsDraftNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            saveAsDraftNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(saveAsDraftNode)

        saveTestXmlNode = settingsDoc.createElement("save_test_xml")
        if self.chkSaveTestXml.GetValue():
            saveTestXmlNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            saveTestXmlNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(saveTestXmlNode)

        csvExistingMetadataNode = settingsDoc.createElement("existing_metadata_mode")
        csvExistingMetadataNode.appendChild(
            settingsDoc.createTextNode(str(self.cmbExistingMetadataMode.GetSelection()))
        )
        rootNode.appendChild(csvExistingMetadataNode)

        appendAttachmentsNode = settingsDoc.createElement("append_attachments")
        if self.chkAppendAttachments.GetValue():
            appendAttachmentsNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            appendAttachmentsNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(appendAttachmentsNode)

        createNewVersionsNode = settingsDoc.createElement("create_new_versions")
        if self.chkCreateNewVersions.GetValue():
            createNewVersionsNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            createNewVersionsNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(createNewVersionsNode)

        useEBIUsernameNode = settingsDoc.createElement("use_ebi_username")
        if self.chkUseEBIUsername.GetValue():
            useEBIUsernameNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            useEBIUsernameNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(useEBIUsernameNode)

        ignoreNonexistentCollaboratorsNode = settingsDoc.createElement(
            "ignore_nonexistent_collaborators"
        )
        if self.chkIgnoreNonexistentCollaborators.GetValue():
            ignoreNonexistentCollaboratorsNode.appendChild(
                settingsDoc.createTextNode("True")
            )
        else:
            ignoreNonexistentCollaboratorsNode.appendChild(
                settingsDoc.createTextNode("False")
            )
        rootNode.appendChild(ignoreNonexistentCollaboratorsNode)

        saveNonexistentUsernamesAsIDsNode = settingsDoc.createElement(
            "save_nonexistent_usernames_as_ids"
        )
        if self.chkSaveNonexistentUsernamesAsIDs.GetValue():
            saveNonexistentUsernamesAsIDsNode.appendChild(
                settingsDoc.createTextNode("True")
            )
        else:
            saveNonexistentUsernamesAsIDsNode.appendChild(
                settingsDoc.createTextNode("False")
            )
        rootNode.appendChild(saveNonexistentUsernamesAsIDsNode)

        attachmentsBasepathNode = settingsDoc.createElement("attachments_basepath")
        if self.txtAttachmentsBasepath.GetValue().strip() != "":
            attachmentsBasepathNode.appendChild(
                settingsDoc.createTextNode(self.txtAttachmentsBasepath.GetValue())
            )
        rootNode.appendChild(attachmentsBasepathNode)

        exportNode = settingsDoc.createElement("export")
        if self.chkExport.GetValue():
            exportNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            exportNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(exportNode)

        includeNonLiveNode = settingsDoc.createElement("include_non_live")
        if self.chkIncludeNonLive.GetValue():
            includeNonLiveNode.appendChild(settingsDoc.createTextNode("True"))
        else:
            includeNonLiveNode.appendChild(settingsDoc.createTextNode("False"))
        rootNode.appendChild(includeNonLiveNode)

        csvOverwriteNode = settingsDoc.createElement("overwrite_mode")
        csvOverwriteNode.appendChild(
            settingsDoc.createTextNode(str(self.cmbConflicts.GetSelection()))
        )
        rootNode.appendChild(csvOverwriteNode)

        whereClauseBasepathNode = settingsDoc.createElement("where_clause")
        if self.txtWhereClause.GetValue().strip() != "":
            whereClauseBasepathNode.appendChild(
                settingsDoc.createTextNode(self.txtWhereClause.GetValue())
            )
        rootNode.appendChild(whereClauseBasepathNode)

        startScriptNode = settingsDoc.createElement("start_script")
        if self.startScript != "":
            startScriptNode.appendChild(settingsDoc.createTextNode(self.startScript))
        rootNode.appendChild(startScriptNode)

        endScriptNode = settingsDoc.createElement("end_script")
        if self.endScript != "":
            endScriptNode.appendChild(settingsDoc.createTextNode(self.endScript))
        rootNode.appendChild(endScriptNode)

        rowPreScriptNode = settingsDoc.createElement("row_pre_script")
        if self.preScript != "":
            rowPreScriptNode.appendChild(settingsDoc.createTextNode(self.preScript))
        rootNode.appendChild(rowPreScriptNode)

        rowPostScriptNode = settingsDoc.createElement("row_post_script")
        if self.postScript != "":
            rowPostScriptNode.appendChild(settingsDoc.createTextNode(self.postScript))
        rootNode.appendChild(rowPostScriptNode)

        # get folder from properties file
        openDir = os.getcwd()
        try:
            self.config.read(self.propertiesFile)
            openDir = os.path.dirname(self.config.get("State", "settingsfile"))
        except:
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.engine.echo(
                    "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    ),
                    log=False,
                    style=2,
                )

        itemSaved = False
        filenameSelected = False
        path = ""

        # display save dialog if not automatically overwriting existing settings file
        if not overwrite or not self.settingsFile.endswith(".ebi"):

            # get default filename
            defaultFilename = os.path.basename(self.settingsFile)
            if defaultFilename.endswith(".ebi"):
                defaultFilename = defaultFilename[:-4]
            try:
                dlg = wx.FileDialog(
                    self,
                    message="Save settings",
                    defaultDir=openDir,
                    defaultFile=defaultFilename,
                    wildcard="EBI settings file (*.ebi)|*.ebi",
                    style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                )
            except:
                # catch error caused by Ubuntu wxPython lack of support for wx.FD_OVERWRITE_PROMPT
                dlg = wx.FileDialog(
                    self,
                    message="Save settings",
                    defaultDir=openDir,
                    defaultFile=defaultFilename,
                    wildcard="EBI settings file (*.ebi)|*.ebi",
                    style=wx.FD_SAVE,
                )
            if dlg.ShowModal() == wx.ID_OK:
                filenameSelected = True
                path = dlg.GetPath()
                self.settingsfile = path
                self.settingsFile = path
            dlg.Destroy()
        else:
            path = self.settingsFile

        # write to settings file if one slected or automatically overwriting existing settings file
        if filenameSelected or (overwrite and self.settingsFile.endswith(".ebi")):

            # force an extension as macintosh does not add one
            if not path.endswith(".ebi"):
                path += ".ebi"

            # save settings file as utf-8
            # toprettyxml with encoding returns bytes, decode to string for text mode
            try:
                fp = open(path, "w", encoding="utf-8")
                fp.write(settingsDoc.toprettyxml(encoding="utf-8").decode("utf-8"))
                fp.close()

                # Also save to persistent settings.json for auto-fill on next startup
                self.settingsManager.set("institution_url", self.txtInstitutionUrl.GetValue().strip())
                self.settingsManager.set("username", self.txtUsername.GetValue().strip())
                self.settingsManager.set("password", self.txtPassword.GetValue())
                self.settingsManager.set("oauth_client_id", self.txtOAuthClientId.GetValue().strip())
                self.settingsManager.save()
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    self.engine.echo(
                        "".join(
                            str(line)
                            for line in traceback.format_exception(
                                exceptionType, exceptionValue, exceptionTraceback
                            )
                        ),
                        log=False,
                        style=2,
                    )

                dlgError = wx.MessageDialog(
                    self,
                    "Unable to save settings file.\n\n" + str(sys.exc_info()[1]),
                    "Settings Save Error",
                    wx.OK | wx.ICON_ERROR,
                )
                dlgError.ShowModal()
                dlgError.Destroy()

                self.SetCursor(self.normalCursor)
                return False

            self.settingsFile = path
            self.settingsfile = path
            self.SetTitle("%s - EBI" % os.path.basename(self.settingsFile))

            self.dirtyUI = False
            itemSaved = True

            # save path to properties file
            try:
                if not "State" in self.config.sections():
                    self.config.add_section("State")
                self.config.set("State", "settingsfile", self.settingsFile)
                self.config.write(open(self.propertiesFile, "w"))
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    self.engine.echo(
                        "".join(
                            str(line)
                            for line in traceback.format_exception(
                                exceptionType, exceptionValue, exceptionTraceback
                            )
                        ),
                        log=False,
                        style=2,
                    )
        time.sleep(0.25)
        self.SetCursor(self.normalCursor)

        return itemSaved

    def getText(self, element):
        rc = []
        for node in element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return "".join(rc)

    def loadSettings(self, path):
        try:
            self.settingsfile = path

            # open settings file as utf-8
            fp = codecs.open(
                path, "r", "utf-8-sig"
            )  # utf-8-sig automatically handles BOM
            settingsString = fp.read()
            fp.close()

            # Python 3: parseString expects bytes, so encode the string
            settingsDoc = parseString(settingsString.encode("utf-8"))

            # set connection fields
            self.txtInstitutionUrl.SetValue(
                self.getText(settingsDoc.getElementsByTagName("institution_url")[0])
            )
            self.txtUsername.SetValue(
                self.getText(settingsDoc.getElementsByTagName("username")[0])
            )
            if len(settingsDoc.getElementsByTagName("password")) > 0:
                self.txtPassword.SetValue(
                    self.dc(
                        self.getText(settingsDoc.getElementsByTagName("password")[0])
                    )
                )
            self.txtCSVPath.SetValue(
                self.getText(settingsDoc.getElementsByTagName("csv_location")[0])
            )

            # set row filter
            if len(settingsDoc.getElementsByTagName("row_filter")) > 0:
                self.txtRowFilter.SetValue(
                    self.getText(settingsDoc.getElementsByTagName("row_filter")[0])
                )
            else:
                self.txtRowFilter.SetValue("")

            # load collections drop down
            collection = self.getText(settingsDoc.getElementsByTagName("collection")[0])
            self.cmbCollections.Clear()
            self.cmbCollections.Append(collection)
            self.cmbCollections.SetStringSelection(collection)

            # set CSV encoding option
            self.cmbEncoding.SetSelection(
                self.cmbEncoding.FindString(
                    self.getText(settingsDoc.getElementsByTagName("csv_encoding")[0])
                )
            )

            # delete all rows
            if self.columnsGrid.GetNumberRows() > 0:
                self.columnsGrid.DeleteRows(0, self.columnsGrid.GetNumberRows())

            # populate grid
            row = 0
            for columnNode in settingsDoc.getElementsByTagName("columns")[
                0
            ].getElementsByTagName("column"):
                self.columnsGrid.AppendRows()

                colPos = str(row + 1) + "- " + self.GetExcelColumnName(row + 1)

                self.columnsGrid.SetCellValue(row, 0, colPos)
                self.columnsGrid.SetCellValue(
                    row, 1, self.getText(columnNode.getElementsByTagName("heading")[0])
                )
                self.columnsGrid.SetCellValue(
                    row,
                    2,
                    self.getText(
                        columnNode.getElementsByTagName("column_data_type")[0]
                    ),
                )
                self.columnsGrid.SetCellValue(
                    row, 3, self.getText(columnNode.getElementsByTagName("display")[0])
                )
                self.columnsGrid.SetCellValue(
                    row,
                    4,
                    self.getText(
                        columnNode.getElementsByTagName("source_identifier")[0]
                    ),
                )
                self.columnsGrid.SetCellValue(
                    row,
                    5,
                    self.getText(columnNode.getElementsByTagName("xml_fragment")[0]),
                )
                self.columnsGrid.SetCellValue(
                    row,
                    6,
                    self.getText(columnNode.getElementsByTagName("delimiter")[0]),
                )

                # set cell alignment
                self.columnsGrid.SetCellAlignment(
                    row, 3, wx.ALIGN_CENTER, wx.ALIGN_CENTER
                )
                self.columnsGrid.SetCellAlignment(
                    row, 4, wx.ALIGN_CENTER, wx.ALIGN_CENTER
                )
                self.columnsGrid.SetCellAlignment(
                    row, 5, wx.ALIGN_CENTER, wx.ALIGN_CENTER
                )
                self.columnsGrid.SetCellAlignment(
                    row, 6, wx.ALIGN_CENTER, wx.ALIGN_CENTER
                )

                # set cell editors (drop-downs) using GridCellAttr
                attr2 = wx.grid.GridCellAttr()
                attr2.SetEditor(
                    wx.grid.GridCellChoiceEditor(
                        [
                            self.METADATA,
                            self.ATTACHMENTLOCATIONS,
                            self.ATTACHMENTNAMES,
                            self.CUSTOMATTACHMENTS,
                            self.RAWFILES,
                            self.URLS,
                            self.HYPERLINKNAMES,
                            self.EQUELLARESOURCES,
                            self.EQUELLARESOURCENAMES,
                            self.COMMANDS,
                            self.TARGETIDENTIFIER,
                            self.TARGETVERSION,
                            self.COLLECTION,
                            self.OWNER,
                            self.COLLABORATORS,
                            self.ITEMID,
                            self.ITEMVERSION,
                            self.THUMBNAILS,
                            self.SELECTEDTHUMBNAIL,
                            self.ROWERROR,
                            self.IGNORE,
                        ],
                        False,
                    )
                )
                self.columnsGrid.SetAttr(row, 2, attr2)

                attr3 = wx.grid.GridCellAttr()
                boolEditor3 = wx.grid.GridCellBoolEditor()
                try:
                    boolEditor3.UseStringValues("YES", "")
                except:
                    pass
                attr3.SetEditor(boolEditor3)
                self.columnsGrid.SetAttr(row, 3, attr3)

                attr4 = wx.grid.GridCellAttr()
                boolEditor4 = wx.grid.GridCellBoolEditor()
                try:
                    boolEditor4.UseStringValues("YES", "")
                except:
                    pass
                attr4.SetEditor(boolEditor4)
                self.columnsGrid.SetAttr(row, 4, attr4)

                attr5 = wx.grid.GridCellAttr()
                boolEditor5 = wx.grid.GridCellBoolEditor()
                try:
                    boolEditor5.UseStringValues("YES", "")
                except:
                    pass
                attr5.SetEditor(boolEditor5)
                self.columnsGrid.SetAttr(row, 5, attr5)

                # set first two cells of each row read-only
                self.columnsGrid.SetReadOnly(row, 0)
                self.columnsGrid.SetReadOnly(row, 1)

                self.setCellStates(row)

                row += 1

            # populate Options

            # set save-as-draft option
            if len(settingsDoc.getElementsByTagName("save_as_draft")) > 0:
                if (
                    self.getText(settingsDoc.getElementsByTagName("save_as_draft")[0])
                    == "True"
                ):
                    self.chkSaveAsDraft.SetValue(True)
                else:
                    self.chkSaveAsDraft.SetValue(False)
            else:
                self.chkSaveAsDraft.SetValue(False)

            # set Save Test XML option
            if len(settingsDoc.getElementsByTagName("save_test_xml")) > 0:
                if (
                    self.getText(settingsDoc.getElementsByTagName("save_test_xml")[0])
                    == "True"
                ):
                    self.chkSaveTestXml.SetValue(True)
                else:
                    self.chkSaveTestXml.SetValue(False)
            else:
                self.chkSaveTestXml.SetValue(False)

            # set existing metadata mode based on deprecated append metadata option
            if len(settingsDoc.getElementsByTagName("append_metadata")) > 0:
                if (
                    self.getText(settingsDoc.getElementsByTagName("append_metadata")[0])
                    == "True"
                ):
                    self.cmbExistingMetadataMode.SetSelection(2)
                else:
                    self.cmbExistingMetadataMode.SetSelection(0)
            else:
                self.cmbExistingMetadataMode.SetSelection(0)

            # set existing metadata mode
            if len(settingsDoc.getElementsByTagName("existing_metadata_mode")) > 0:
                self.cmbExistingMetadataMode.SetSelection(
                    int(
                        self.getText(
                            settingsDoc.getElementsByTagName("existing_metadata_mode")[
                                0
                            ]
                        )
                    )
                )

            # set append attachments option
            if len(settingsDoc.getElementsByTagName("append_attachments")) > 0:
                if (
                    self.getText(
                        settingsDoc.getElementsByTagName("append_attachments")[0]
                    )
                    == "True"
                ):
                    self.chkAppendAttachments.SetValue(True)
                else:
                    self.chkAppendAttachments.SetValue(False)
            else:
                self.chkAppendAttachments.SetValue(False)

            # set create new versions option
            if len(settingsDoc.getElementsByTagName("create_new_versions")) > 0:
                if (
                    self.getText(
                        settingsDoc.getElementsByTagName("create_new_versions")[0]
                    )
                    == "True"
                ):
                    self.chkCreateNewVersions.SetValue(True)
                else:
                    self.chkCreateNewVersions.SetValue(False)
            else:
                self.chkCreateNewVersions.SetValue(False)

            # set use EBI username option
            if len(settingsDoc.getElementsByTagName("use_ebi_username")) > 0:
                if (
                    self.getText(
                        settingsDoc.getElementsByTagName("use_ebi_username")[0]
                    )
                    == "True"
                ):
                    self.chkUseEBIUsername.SetValue(True)
                else:
                    self.chkUseEBIUsername.SetValue(False)
            else:
                self.chkUseEBIUsername.SetValue(False)

            # set ignore non-existent collaborators option
            if (
                len(
                    settingsDoc.getElementsByTagName("ignore_nonexistent_collaborators")
                )
                > 0
            ):
                if (
                    self.getText(
                        settingsDoc.getElementsByTagName(
                            "ignore_nonexistent_collaborators"
                        )[0]
                    )
                    == "True"
                ):
                    self.chkIgnoreNonexistentCollaborators.SetValue(True)
                else:
                    self.chkIgnoreNonexistentCollaborators.SetValue(False)
            else:
                self.chkIgnoreNonexistentCollaborators.SetValue(False)

            # set save non-existent usernames as IDs option
            if (
                len(
                    settingsDoc.getElementsByTagName(
                        "save_nonexistent_usernames_as_ids"
                    )
                )
                > 0
            ):
                if (
                    self.getText(
                        settingsDoc.getElementsByTagName(
                            "save_nonexistent_usernames_as_ids"
                        )[0]
                    )
                    == "True"
                ):
                    self.chkSaveNonexistentUsernamesAsIDs.SetValue(True)
                else:
                    self.chkSaveNonexistentUsernamesAsIDs.SetValue(False)
            else:
                self.chkSaveNonexistentUsernamesAsIDs.SetValue(False)

            # set attachments basepath option
            if len(settingsDoc.getElementsByTagName("attachments_basepath")) > 0:
                self.txtAttachmentsBasepath.SetValue(
                    self.getText(
                        settingsDoc.getElementsByTagName("attachments_basepath")[0]
                    )
                )
            else:
                self.txtAttachmentsBasepath.SetValue("")

            # set export
            if len(settingsDoc.getElementsByTagName("export")) > 0:
                if (
                    self.getText(settingsDoc.getElementsByTagName("export")[0])
                    == "True"
                ):
                    self.chkExport.SetValue(True)
                else:
                    self.chkExport.SetValue(False)
            else:
                self.chkExport.SetValue(False)

            self.UpdateImportExportButtons()

            # set export include non-live
            if len(settingsDoc.getElementsByTagName("include_non_live")) > 0:
                if (
                    self.getText(
                        settingsDoc.getElementsByTagName("include_non_live")[0]
                    )
                    == "True"
                ):
                    self.chkIncludeNonLive.SetValue(True)
                else:
                    self.chkIncludeNonLive.SetValue(False)
            else:
                self.chkIncludeNonLive.SetValue(False)

            # set overwrite mode
            if len(settingsDoc.getElementsByTagName("overwrite_mode")) > 0:
                self.cmbConflicts.SetSelection(
                    int(
                        self.getText(
                            settingsDoc.getElementsByTagName("overwrite_mode")[0]
                        )
                    )
                )

            # set where clause
            if len(settingsDoc.getElementsByTagName("where_clause")) > 0:
                self.txtWhereClause.SetValue(
                    self.getText(settingsDoc.getElementsByTagName("where_clause")[0])
                )
            else:
                self.txtWhereClause.SetValue("")

            # set start script
            if len(settingsDoc.getElementsByTagName("start_script")) > 0:
                self.startScript = self.getText(
                    settingsDoc.getElementsByTagName("start_script")[0]
                )
            else:
                self.startScript = ""

            # set end script
            if len(settingsDoc.getElementsByTagName("end_script")) > 0:
                self.endScript = self.getText(
                    settingsDoc.getElementsByTagName("end_script")[0]
                )
            else:
                self.endScript = ""

            # set row pre-script
            if len(settingsDoc.getElementsByTagName("row_pre_script")) > 0:
                self.preScript = self.getText(
                    settingsDoc.getElementsByTagName("row_pre_script")[0]
                )
            else:
                self.preScript = ""

            # set row post-script
            if len(settingsDoc.getElementsByTagName("row_post_script")) > 0:
                self.postScript = self.getText(
                    settingsDoc.getElementsByTagName("row_post_script")[0]
                )
            else:
                self.postScript = ""

            self.updateScriptButtonsLabels()

            self.settingsFile = path
            self.SetTitle("%s - EBI" % os.path.basename(self.settingsFile))
            self.mainStatusBar.SetStatusText("Ready", 0)

            self.dirtyUI = False

            return True

        except:
            # form error string for debugging
            err = str(sys.exc_info()[1])
            errorString = "ERROR opening settings file: " + err
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            if self.debug:
                errorString += ": " + "".join(
                    str(line)
                    for line in traceback.format_exception(
                        exceptionType, exceptionValue, exceptionTraceback
                    )
                )
            self.engine.echo(errorString, log=False, style=2)
            self.mainStatusBar.SetStatusText("Ready", 0)
            return False

    def OnMainToolbarSaveTool(self, event):
        if event.GetId() == wxID_MAINFRAMEMAINTOOLBARSAVE:
            # save settings
            self.saveSettings()

        if event.GetId() == wxID_MAINFRAMEMAINTOOLBAROPEN:

            # get folder from properties file
            openDir = os.getcwd()
            try:
                self.config.read(self.propertiesFile)
                if self.config.has_option("State", "settingsfile"):
                    openDir = os.path.dirname(self.config.get("State", "settingsfile"))
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    self.engine.echo(
                        "".join(
                            str(line)
                            for line in traceback.format_exception(
                                exceptionType, exceptionValue, exceptionTraceback
                            )
                        ),
                        log=False,
                        style=2,
                    )

            # open settings file
            dlg = wx.FileDialog(
                self,
                message="Open EBI settings file",
                defaultDir=openDir,
                defaultFile="",
                wildcard="EBI settings file (*.ebi)|*.ebi",
                style=wx.FD_OPEN | wx.FD_CHANGE_DIR,
            )

            if dlg.ShowModal() == wx.ID_OK:
                if not self.loadSettings(dlg.GetPaths()[0]):
                    dlgError = wx.MessageDialog(
                        None,
                        "Error opening settings file\n\n" + str(sys.exc_info()[1]),
                        "Settings File Error",
                        wx.OK | wx.ICON_ERROR,
                    )
                    dlgError.ShowModal()
                    dlgError.Destroy()

                # save path to properties file
                try:
                    if not self.config.has_section("State"):
                        self.config.add_section("State")
                    self.config.set("State", "settingsfile", self.settingsFile)
                    self.config.write(open(self.propertiesFile, "w"))
                except:
                    if self.debug:
                        exceptionType, exceptionValue, exceptionTraceback = (
                            sys.exc_info()
                        )
                        self.engine.echo(
                            "".join(
                                str(line)
                                for line in traceback.format_exception(
                                    exceptionType, exceptionValue, exceptionTraceback
                                )
                            ),
                            log=False,
                            style=2,
                        )

            dlg.Destroy()

        if event.GetId() == wxID_MAINFRAMEMAINTOOLBARSTOP:
            # stop processing
            self.engine.StopProcessing = True
            self.engine.pause = False
            self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSTOP, False)
            self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARPAUSE, False)

        if event.GetId() == wxID_MAINFRAMEMAINTOOLBARPAUSE:
            # pause/unpause processing
            if self.engine.pause:
                self.engine.pause = False
            else:
                self.engine.pause = True

        if event.GetId() == wxID_MAINFRAMEMAINTOOLBAROPTIONS:
            dlg = OptionsDialog.OptionsDialog(self)
            dlg.CenterOnScreen()

            # populate dialog with preferences
            if "Configuration" in self.config.sections() and self.config.getboolean(
                "Configuration", "loadlastsettingsfile"
            ):
                dlg.chkLoadLastSettingsFile.SetValue(True)
            dlg.chkClearLogEachRun.SetValue(self.clearLogEachRun)
            dlg.chkSavePassword.SetValue(self.savePassword)
            dlg.chkDebugMode.SetValue(self.debug)
            dlg.chkNetworkLogging.SetValue(self.engine.networkLogging)
            dlg.txtAttachmentsChunkSize.SetValue(str(self.engine.chunkSize))
            dlg.txtLogBufferSize.SetValue(str(self.log.logBufferSize))
            dlg.txtProxyAddress.SetValue(str(self.engine.proxy))
            dlg.txtProxyUsername.SetValue(str(self.engine.proxyUsername))
            dlg.txtProxyPassword.SetValue(str(self.engine.proxyPassword))

            # Load OAuth/Auth settings from SettingsManager
            dlg.txtInstitutionUrl.SetValue(self.settingsManager.get("institution_url", ""))
            dlg.txtOAuthClientId.SetValue(self.settingsManager.get("oauth_client_id", ""))
            dlg.txtOAuthRedirectUri.SetValue(
                self.settingsManager.get("oauth_redirect_uri", "default")
            )

            # this does not return until the dialog is closed.
            val = dlg.ShowModal()

            if val == wx.ID_OK:
                # set preferences from dialog

                try:
                    if not "Configuration" in self.config.sections():
                        self.config.add_section("Configuration")

                    self.config.set(
                        "Configuration",
                        "loadlastsettingsfile",
                        str(dlg.chkLoadLastSettingsFile.GetValue()).lower(),
                    )

                    self.config.set(
                        "Configuration",
                        "debug",
                        str(dlg.chkDebugMode.GetValue()).lower(),
                    )
                    self.debug = dlg.chkDebugMode.GetValue()
                    self.engine.debug = dlg.chkDebugMode.GetValue()

                    self.config.set(
                        "Configuration",
                        "clearlogeachrun",
                        str(dlg.chkClearLogEachRun.GetValue()).lower(),
                    )
                    self.clearLogEachRun = dlg.chkClearLogEachRun.GetValue()

                    self.config.set(
                        "Configuration",
                        "savepassword",
                        str(dlg.chkSavePassword.GetValue()).lower(),
                    )
                    self.savePassword = dlg.chkSavePassword.GetValue()

                    self.config.set(
                        "Configuration",
                        "networklogging",
                        str(dlg.chkNetworkLogging.GetValue()).lower(),
                    )
                    self.engine.networkLogging = dlg.chkNetworkLogging.GetValue()

                    if dlg.txtAttachmentsChunkSize.GetValue().strip() == "":
                        self.engine.chunkSize = self.engine.defaultChunkSize
                        self.config.set(
                            "Configuration",
                            "attachmentchunksize",
                            self.engine.defaultChunkSize,
                        )
                    else:
                        try:
                            self.engine.chunkSize = int(
                                dlg.txtAttachmentsChunkSize.GetValue()
                            )
                            self.config.set(
                                "Configuration",
                                "attachmentchunksize",
                                str(dlg.txtAttachmentsChunkSize.GetValue()),
                            )
                        except:
                            pass

                    self.engine.proxy = dlg.txtProxyAddress.GetValue().strip()
                    self.config.set("Configuration", "proxyaddress", self.engine.proxy)
                    self.engine.proxyUsername = dlg.txtProxyUsername.GetValue().strip()
                    self.config.set(
                        "Configuration", "proxyusername", self.engine.proxyUsername
                    )
                    self.engine.proxyPassword = dlg.txtProxyPassword.GetValue().strip()
                    if self.engine.proxyPassword != "":
                        self.config.set(
                            "Configuration",
                            "proxypassword",
                            self.ec(self.engine.proxyPassword),
                        )
                    else:
                        self.config.set("Configuration", "proxypassword", "")

                    if dlg.txtLogBufferSize.GetValue().strip() == "":
                        self.log.logBufferSize = self.log.defaultLogBufferSize
                        self.config.set(
                            "Configuration",
                            "logbuffersize",
                            self.log.defaultLogBufferSize,
                        )
                    else:
                        try:
                            self.log.logBufferSize = int(
                                dlg.txtLogBufferSize.GetValue()
                            )
                            self.config.set(
                                "Configuration",
                                "logbuffersize",
                                str(dlg.txtLogBufferSize.GetValue()),
                            )
                        except:
                            pass

                    # Save OAuth/Auth settings to SettingsManager
                    self.settingsManager.set(
                        "institution_url", dlg.txtInstitutionUrl.GetValue().strip()
                    )
                    self.settingsManager.set(
                        "oauth_client_id", dlg.txtOAuthClientId.GetValue().strip()
                    )
                    self.settingsManager.set(
                        "oauth_redirect_uri",
                        dlg.txtOAuthRedirectUri.GetValue().strip() or "default",
                    )
                    self.settingsManager.save()

                    self.config.write(open(self.propertiesFile, "w"))
                except:
                    if self.debug:
                        exceptionType, exceptionValue, exceptionTraceback = (
                            sys.exc_info()
                        )
                        self.engine.echo(
                            "".join(
                                str(line)
                                for line in traceback.format_exception(
                                    exceptionType, exceptionValue, exceptionTraceback
                                )
                            ),
                            log=False,
                            style=2,
                        )

            dlg.Destroy()

        if event.GetId() == wxID_MAINFRAMEMAINTOOLBARABOUT:

            # lookup what the latest EBI version is
            try:
                self.SetCursor(self.waitCursor)
                ebiVersion = ""
                if self.engine.proxy != "":

                    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                    password_mgr.add_password(
                        None,
                        self.engine.proxy,
                        self.engine.proxyUsername,
                        self.engine.proxyPassword,
                    )
                    proxy_auth_handler = urllib.request.ProxyBasicAuthHandler(
                        password_mgr
                    )
                    proxy_handler = urllib.request.ProxyHandler(
                        {"http": self.engine.proxy}
                    )

                    # build URL opener with proxy
                    opener = urllib.request.build_opener(
                        proxy_handler, proxy_auth_handler
                    )

                    f = opener.open(self.EBIDownloadPage + "<XML>")
                else:
                    f = urllib.request.urlopen(self.EBIDownloadPage + "<XML>")

                itemXml = PropBagEx(parseString(f.read()))
                itemTitle = itemXml.getNode("xml/item/itembody/name").strip()
                ebiVersion = itemTitle[itemTitle.rfind("v") + 1 :]
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    self.engine.echo(
                        "".join(
                            str(line)
                            for line in traceback.format_exception(
                                exceptionType, exceptionValue, exceptionTraceback
                            )
                        ),
                        log=False,
                        style=2,
                    )

            self.SetCursor(self.normalCursor)

            # form latest version text
            latestVersionText = ""
            if ebiVersion != "":
                latestVersionText = "\n(latest version is %s)" % ebiVersion

            # about dialog
            info = wx.adv.AboutDialogInfo()
            info.Name = "EQUELLA(R) Bulk Importer"
            info.Version = self.version + latestVersionText
            info.Copyright = self.copyright
            info.Description = (
                ""
                "The EQUELLA Bulk Importer is a program for uploading content into the award winning \n"
                "EQUELLA(R) content management system.\n\n"
                'Note that the EQUELLA Bulk Importer is provided "as-is". If you wish to have any \n'
                "extensions made to the program or issues resolved please contact Pearson to engage \n"
                "the services of an EQUELLA consultant."
            )
            info.WebSite = (
                self.EBIDownloadPage,
                "Get latest version and documentation",
            )
            info.License = self.license

            # display about box
            wx.adv.AboutBox(info)

    def populateCollectionsDropDown(self, collectionsList):
        selectedCollection = self.cmbCollections.GetStringSelection()
        self.cmbCollections.Clear()
        if len(collectionsList) == 0:
            self.cmbCollections.Append("<No collections>")
        else:
            self.cmbCollections.Append("<Please select>")
        for collection in collectionsList:
            self.cmbCollections.Append(collection)
        self.cmbCollections.SetSelection(0)
        if (
            selectedCollection != "<Please select>"
            and selectedCollection in self.cmbCollections.GetStrings()
        ):
            self.cmbCollections.Delete(0)
            self.cmbCollections.SetSelection(
                self.cmbCollections.FindString(selectedCollection)
            )

    def OnBtnGetCollectionsButton(self, event):

        self.SetCursor(self.waitCursor)
        self.mainStatusBar.SetStatusText("Connecting...", 0)
        try:
            if self.txtInstitutionUrl.GetValue().strip() == "":
                raise Exception("No insitution URL provided")

            # read current connection parameters
            self.loadCurrentSettings()

            # get collection names
            collectionsList = self.engine.getContributableCollections()

            # populate collections drop down
            self.populateCollectionsDropDown(collectionsList)

            self.mainStatusBar.SetStatusText("Connection successful", 0)
            dlg = wx.MessageDialog(
                None,
                "Connection successful and collections retrieved.",
                "Connection Successful",
                wx.OK | wx.ICON_INFORMATION,
            )
            dlg.ShowModal()
            dlg.Destroy()
            self.mainStatusBar.SetStatusText("Ready", 0)

            self.SetCursor(self.normalCursor)

        except:
            self.SetCursor(self.normalCursor)

            errorMessage = self.engine.translateError(str(sys.exc_info()[1]))
            dlg = wx.MessageDialog(
                None,
                "Error connecting to EQUELLA:\n\n" + errorMessage,
                "Connection Error",
                wx.OK | wx.ICON_ERROR,
            )
            self.engine.echo("Error connecting to EQUELLA: " + errorMessage, style=2)

            # form error string for debugging
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.engine.echo(
                    "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    ),
                    log=False,
                    style=2,
                )

            dlg.ShowModal()
            dlg.Destroy()

            self.mainStatusBar.SetStatusText("Ready", 0)

    def disableControls(self):
        self.btnConnTestImport.Disable()
        self.btnConnStartImport.Disable()
        self.btnCsvTestImport.Disable()
        self.btnCsvStartImport.Disable()
        self.btnOptionsTestImport.Disable()
        self.btnOptionsStartImport.Disable()
        self.btnLogTestImport.Disable()
        self.btnLogStartImport.Disable()
        self.btnBrowseCSV.Disable()
        self.btnReloadCSV.Disable()
        self.btnGetCollections.Disable()
        self.btnGetCollections.Disable()
        self.columnsGrid.Disable()
        self.cmbCollections.Disable()
        self.txtCSVPath.Disable()
        self.txtRowFilter.Disable()
        self.cmbEncoding.Disable()
        self.txtInstitutionUrl.Disable()
        self.txtPassword.Disable()
        self.txtUsername.Disable()
        self.optionsPage.Disable()
        self.btnClearLog.Disable()
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBAROPEN, False)
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSAVE, False)
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBAROPTIONS, False)

    def enableControls(self):
        self.btnConnTestImport.Enable()
        self.btnConnStartImport.Enable()
        self.btnCsvTestImport.Enable()
        self.btnCsvStartImport.Enable()
        self.btnOptionsTestImport.Enable()
        self.btnOptionsStartImport.Enable()
        self.btnLogTestImport.Enable()
        self.btnLogStartImport.Enable()
        self.btnBrowseCSV.Enable()
        self.btnReloadCSV.Enable()
        self.btnGetCollections.Enable()
        self.btnGetCollections.Enable()
        self.columnsGrid.Enable()
        self.cmbCollections.Enable()
        self.txtCSVPath.Enable()
        self.txtRowFilter.Enable()
        self.cmbEncoding.Enable()
        self.txtInstitutionUrl.Enable()
        self.txtPassword.Enable()
        self.txtUsername.Enable()
        self.optionsPage.Enable()
        self.btnClearLog.Enable()
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBAROPEN, True)
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSAVE, True)
        self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBAROPTIONS, True)

    def OnBtnStartImportButton(self, event):
        self.startImport(testOnly=False)

    def OnBtnTestImportButton(self, event):
        self.startImport(testOnly=True)

    def startImport(self, testOnly):
        try:
            # Mac bug workaround: commit any changed but uncommitted cells in wxGrid
            self.columnsGrid.SetGridCursor(
                self.columnsGrid.GetGridCursorRow(), self.columnsGrid.GetGridCursorCol()
            )
        except:
            pass
        try:
            self.progressGauge.SetSize((self.progressBarWidth, self.progressBarHeight))
            self.progressGauge.Hide()

            if self.txtInstitutionUrl.GetValue().strip() == "":
                raise Exception("No institution URL provided")
            if (
                self.cmbCollections.GetStringSelection() == "<No collections>"
                or self.cmbCollections.GetStringSelection() == "<Please select>"
            ):
                try:
                    self.loadCurrentSettings()
                    self.populateCollectionsDropDown(
                        sorted(self.engine.getContributableCollections())
                    )
                except:
                    pass
                raise Exception("No collection selected")
            if self.getCSVPath() == "":
                raise Exception("No CSV selected")
            # clear log if required
            if self.clearLogEachRun:
                self.ClearLog()

            if self.verifyCurrentColumnsMatchCSV():
                self.disableControls()
                self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSTOP, True)
                self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARPAUSE, True)

                # select log page (tab)
                self.nb.SetSelection(3)

                # read current connection parameters and run import
                self.loadCurrentSettings()

                # print(preferences)
                self.printNonDefaultPreferences()

                # perform run
                self.log.Disable()
                self.engine.runImport(self, testOnly)
                self.log.Enable()

                self.enableControls()
                self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSTOP, False)
                self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARPAUSE, False)

                self.progressGauge.SetSize((0, self.progressBarHeight))
                self.progressGauge.SetValue(0)

            else:
                # select csv page (tab)
                self.nb.SetSelection(1)

                dlg = wx.MessageDialog(
                    None,
                    "CSV headings do not match the column headings in the settings.\n\nThe CSV headings may have been changed. Try reloading the CSV or modify the CSV to match the settings.",
                    "CSV Load Error",
                    wx.OK | wx.ICON_ERROR,
                )
                dlg.ShowModal()
                dlg.Destroy()

            # (re)populate collections drop down
            if len(self.engine.collectionIDs) > 0:
                self.populateCollectionsDropDown(
                    sorted(self.engine.collectionIDs.keys())
                )

        except:
            self.progressGauge.Hide()

            # select log page (tab)
            self.nb.SetSelection(3)
            self.log.Enable()

            # form error string for debugging
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            errorString = "ERROR: " + str(exceptionValue)
            if self.debug:
                errorString += ": " + "".join(
                    str(line)
                    for line in traceback.format_exception(
                        exceptionType, exceptionValue, exceptionTraceback
                    )
                )
            self.engine.echo(errorString, log=False, style=2)
            self.enableControls()
            self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARSTOP, False)
            self.mainToolbar.EnableTool(wxID_MAINFRAMEMAINTOOLBARPAUSE, False)

    def OnClose(self, event):
        # save main frame dimensions to properties file
        try:
            if not "State" in self.config.sections():
                self.config.add_section("State")
            self.config.set("State", "mainframesize", self.GetClientSize())
            self.config.write(open(self.propertiesFile, "w"))
        except:
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.engine.echo(
                    "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    ),
                    log=False,
                    style=2,
                )

        if self.dirtyUI:
            dlg = wx.MessageDialog(
                self,
                "Do you want to save your settings before exiting?",
                "Save Settings",
                wx.YES | wx.NO | wx.CANCEL | wx.ICON_EXCLAMATION,
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_CANCEL:
                event.Veto()
                return
            if result == wx.ID_YES:
                # save settings
                if not self.saveSettings(True):
                    event.Veto()
                    return

        # Clean up to prevent bus error on macOS
        try:
            self.SetCursor(wx.NullCursor)
        except:
            pass

        event.Skip()


class Log(stc.StyledTextCtrl):
    def __init__(
        self, parent, ID=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0
    ):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)
        self.parent = parent
        self.defaultLogBufferSize = 1000
        self.logBufferSize = self.defaultLogBufferSize
        self.logBufferChunk = 100
        self.SetReadOnly(True)

        if wx.Platform == "__WXMSW__":
            faces = {
                "mono": "Courier New",
                "size": 10,
            }
        elif wx.Platform == "__WXMAC__":
            faces = {
                "mono": "Monaco",
                "size": 12,
            }
        else:
            faces = {
                "mono": "Courier",
                "size": 12,
            }

        # default style
        self.StyleSetSpec(
            stc.STC_STYLE_DEFAULT, "fore:#0000FF,face:%(mono)s,size:%(size)d" % faces
        )
        self.StyleClearAll()
        self.StyleSetSpec(1, "fore:#000000")
        self.StyleSetSpec(2, "fore:#ff0000")
        self.StyleSetSpec(3, "fore:#009900")
        self.SetWrapMode(True)

    def AddLogText(self, text, style=0):
        self.SetReadOnly(False)
        # Python 3: decode only if bytes, otherwise use as-is
        if isinstance(text, bytes):
            text = text.decode(self.parent.owner.cmbEncoding.GetStringSelection())
        self.AppendText(text)
        if style != 0:
            self.StartStyling(
                self.GetTextLength() - len(text)
            )  # wxPython 4.x: only position param
            self.SetStyling(len(text) - 1, style)
        if self.GetLineCount() > self.logBufferSize + self.logBufferChunk:
            self.SetSelection(
                0, self.PositionFromLine(self.GetLineCount() - self.logBufferSize)
            )
            self.DeleteBack()

        self.SetReadOnly(True)
        self.GotoPos(self.GetLength())


class ScriptEditor(stc.StyledTextCtrl):

    def __init__(
        self, parent, ID=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0
    ):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)

        self.SetLexer(stc.STC_LEX_PYTHON)
        ebiScriptKeywords = [
            "IMPORT",
            "EXPORT",
            "NEWITEM",
            "NEWVERSION",
            "EDITITEM",
            "DELETEITEM",
            "mode",
            "action",
            "vars",
            "rowData",
            "rowCounter",
            "testOnly",
            "institutionUrl",
            "collection",
            "username",
            "logger",
            "columnHeadings",
            "columnSettings",
            "successCount",
            "errorCount",
            "itemId",
            "itemVersion",
            "xml",
            "xmldom",
            "process",
            "csvData",
            "True",
            "False",
            "sourceIdentifierIndex",
            "targetIdentifierIndex",
            "targetVersionIndex",
            "imsmanifest",
            "ebi",
            "equella",
        ]
        self.SetKeyWords(
            0, " ".join(keyword.kwlist) + " " + " ".join(ebiScriptKeywords)
        )

        self.SetMarginWidth(1, 40)
        self.SetMarginWidth(2, 5)
        self.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        self.SetViewWhiteSpace(False)
        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(160)

        if wx.Platform == "__WXMSW__":
            faces = {
                "times": "Times New Roman",
                "mono": "Courier New",
                "helv": "Arial",
                "other": "Comic Sans MS",
                "size": 10,
                "size2": 8,
            }
        elif wx.Platform == "__WXMAC__":
            faces = {
                "times": "Times New Roman",
                "mono": "Monaco",
                "helv": "Arial",
                "other": "Comic Sans MS",
                "size": 12,
                "size2": 10,
            }
        else:
            faces = {
                "times": "Times",
                "mono": "Courier",
                "helv": "Helvetica",
                "other": "new century schoolbook",
                "size": 12,
                "size2": 10,
            }

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "face:%(mono)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default
        self.StyleSetSpec(
            stc.STC_STYLE_LINENUMBER,
            "back:#C0C0C0,face:%(helv)s,size:%(size2)d" % faces,
        )
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, "fore:#000000,back:#FF0000,bold")

        # Python styles
        # Default
        self.StyleSetSpec(
            stc.STC_P_DEFAULT, "fore:#000000,face:%(mono)s,size:%(size)d" % faces
        )
        # Comments
        self.StyleSetSpec(
            stc.STC_P_COMMENTLINE, "fore:#007F00,face:%(mono)s,size:%(size)d" % faces
        )
        # Number
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        # String
        self.StyleSetSpec(
            stc.STC_P_STRING, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces
        )
        # Single quoted string
        self.StyleSetSpec(
            stc.STC_P_CHARACTER, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces
        )
        # Keyword
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        self.StyleSetSpec(
            stc.STC_P_CLASSNAME, "fore:#0000FF,bold,underline,size:%(size)d" % faces
        )
        # Function or method name definition
        self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
        self.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
        # Identifiers
        self.StyleSetSpec(
            stc.STC_P_IDENTIFIER, "fore:#000000,face:%(mono)s,size:%(size)d" % faces
        )
        # Comment-blocks
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:#7F7F7F,size:%(size)d" % faces)
        # End of line where string is not closed
        self.StyleSetSpec(
            stc.STC_P_STRINGEOL,
            "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces,
        )

        self.SetCaretForeground("BLUE")

        self.SetUseTabs(0)
        self.SetTabWidth(4)
        self.SetTabIndents(1)
        self.SetBackSpaceUnIndents(1)

        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

    def OnKeyUp(self, event):
        key = event.GetKeyCode()

        # auto indent
        if key == wx.WXK_NUMPAD_ENTER or key == wx.WXK_RETURN:
            line = self.GetCurrentLine()
            indentWidth = self.GetLineIndentation(line - 1)

            # add extra indent if following an indent keyword
            indentKeywords = [
                "if ",
                "else:",
                "elif ",
                "for ",
                "while ",
                "def ",
                "class ",
                "try:",
                "except ",
                "finally:",
            ]
            if (
                list(
                    filter(
                        self.GetLineRaw(line - 1).strip().startswith,
                        indentKeywords + [""],
                    )
                )[0]
                in indentKeywords
            ):
                indentWidth += self.GetTabWidth()

            self.SetLineIndentation(line, indentWidth)
            for i in range(indentWidth):
                self.CharRight()

        event.Skip()


class ScriptDialog(wx.Dialog):

    def __init__(self, prnt):
        wx.Dialog.__init__(
            self,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            parent=prnt,
            name="",
            title="Script",
            pos=wx.Point(-1, -1),
            id=-1,
            size=wx.Size(700, 600),
        )

        self.scriptEditor = ScriptEditor(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.scriptEditor, 1, wx.EXPAND)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.ALL, 5)

        self.SetSizer(sizer)
