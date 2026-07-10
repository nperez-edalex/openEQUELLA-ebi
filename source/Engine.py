# Engine.py
#
# Author: Jim Kurian, Pearson plc.
# Date: October 2014
#
# The CSV processing engine of the EQUELLA Bulk Importer. Loads a
# CSV file and iterates through the rows creating items in EQUELLA
# for each one. Utilizes equellaclient41.py for EQUELLA
# communications. Invoked by Mainframe.py.

from xml.dom import Node
from equellaclient import *
import time, datetime
import zipfile, csv, codecs, io
import sys, platform
import traceback
import random
import os
import zipfile, glob, time, getpass, uuid
import urllib.parse
import wx

import Constants
import Utils
from RowProcessor import RowProcessor


class Engine:
    def __init__(self, owner, Version, Copyright):
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
        self.ROWERROR = Constants.ROWERROR
        self.THUMBNAILS = Constants.THUMBNAILS
        self.SELECTEDTHUMBNAIL = Constants.SELECTEDTHUMBNAIL
        self.IGNORE = Constants.IGNORE

        self.COLUMN_POS = Constants.COLUMN_POS
        self.COLUMN_HEADING = Constants.COLUMN_HEADING
        self.COLUMN_DATATYPE = Constants.COLUMN_DATATYPE
        self.COLUMN_DISPLAY = Constants.COLUMN_DISPLAY
        self.COLUMN_SOURCEIDENTIFIER = Constants.COLUMN_SOURCEIDENTIFIER
        self.COLUMN_XMLFRAGMENT = Constants.COLUMN_XMLFRAGMENT
        self.COLUMN_DELIMITER = Constants.COLUMN_DELIMITER

        self.CLEARMETA = Constants.CLEARMETA
        self.REPLACEMETA = Constants.REPLACEMETA
        self.APPENDMETA = Constants.APPENDMETA

        self.OVERWRITENONE = Constants.OVERWRITENONE
        self.OVERWRITEEXISTING = Constants.OVERWRITEEXISTING
        self.OVERWRITEALL = Constants.OVERWRITEALL

        self.pause = False
        self.owner = owner

        # default settings (can be overridden in ebi.properties)
        self.debug = False
        self.attachmentMetadataTargets = True
        self.defaultChunkSize = 1024 * 2048
        self.chunkSize = self.defaultChunkSize
        self.networkLogging = False
        self.scormformatsupport = True

        self.copyright = Copyright
        self.rowFilter = ""
        self.logfilesfolder = "logs"
        self.logfilespath = ""
        self.testItemfolder = "test_output"
        self.receiptFolder = "receipts"
        self.sessionName = ""
        self.maxRetry = 5

        # welcome message for command prompt and log files
        self.welcomeLine1 = "EQUELLA Bulk Importer [EBI %s, %s]" % (
            Version,
            Utils.getPlatform(),
        )
        self.welcomeLine2 = self.copyright + "\n"

        print(self.welcomeLine1)
        print(self.welcomeLine2)

        # CSV and connection settings
        self.institutionUrl = ""
        self.username = ""
        self.password = ""
        self.oauthClientId = ""
        self.oauthRedirectUri = "http://localhost:9999/callback"  # Default to localhost callback
        self.collection = ""
        self.csvFilePath = ""

        # Options
        self.proxy = ""
        self.proxyUsername = ""
        self.proxyPassword = ""
        self.encoding = "utf8"
        self.saveTestXML = False
        self.saveAsDraft = False
        self.saveTestXml = False
        self.existingMetadataMode = self.CLEARMETA
        self.appendAttachments = False
        self.createNewVersions = False
        self.useEBIUsername = False
        self.ignoreNonexistentCollaborators = False
        self.saveNonexistentUsernamesAsIDs = True
        self.attachmentsBasepath = ""
        self.absoluteAttachmentsBasepath = ""
        self.export = False
        self.includeNonLive = False
        self.overwriteMode = self.OVERWRITENONE
        self.whereClause = ""
        self.startScript = ""
        self.endScript = ""
        self.preScript = ""
        self.postScript = ""

        self.ebiScriptObject = EbiScriptObject(self)

        # data structures to store column settings
        self.currentColumns = []
        self.csvArray = []

        self.successCount = 0
        self.errorCount = 0

        # enum for attachment types
        self.attachmentTypeFile = 0
        self.attachmentTypeZip = 1
        self.attachmentTypeIMS = 2
        self.attachmentTypeSCORM = 3

        self.columnHeadings = []
        self.StopProcessing = False
        self.processingStoppedByScript = False
        self.Skip = False
        self.logFileName = ""
        self.collectionIDs = {}

        self.itemSystemNodes = [
            "staging",
            "name",
            "description",
            "itemdefid",
            "datecreated",
            "datemodified",
            "dateforindex",
            "owner",
            "collaborativeowners",
            "rating",
            "badurls",
            "moderation",
            "newitem",
            "attachments",
            "navigationnodes",
            "url",
            "history",
            "thumbnail",
            "itembody",
        ]
        self.sourceIdentifierReceipts = {}
        self.exportedFiles = []
        self.eqVersionmm = ""
        self.eqVersionmmr = ""
        self.eqVersionDisplay = ""

    def getPlatform(self):
        ebiPlatform = "Python " + platform.python_version()
        system = platform.system()
        if system == "Windows":
            ebiPlatform += ", Windows " + platform.release()
        elif system == "Darwin":
            ebiPlatform += ", Mac OS " + platform.mac_ver()[0]
        elif system == "Linux":
            # Use freedesktop_os_release() for Python 3.10+ or fallback for older versions
            try:
                if hasattr(platform, "freedesktop_os_release"):
                    os_info = platform.freedesktop_os_release()
                    ebiPlatform += (
                        ", "
                        + os_info.get("NAME", "Linux")
                        + " "
                        + os_info.get("VERSION", "").strip()
                    )
                else:
                    ebiPlatform += ", Linux " + platform.release()
            except Exception:
                ebiPlatform += ", Linux " + platform.release()
        return ebiPlatform

    def setDebug(self, debug):
        self.debug = debug
        if self.debug:
            self.echo("debug = True")

    def setLog(self, log):
        self.log = log
        self.log.AddLogText(self.welcomeLine1 + "\n", 1)
        self.log.AddLogText(self.welcomeLine2 + "\n", 1)

    def echo(self, entry, display=True, log=True, style=0):

        if log and self.logFileName != "":

            # create/open log file
            logfile = open(
                os.path.join(self.logfilespath, self.logFileName),
                "a",
                encoding=self.encoding,
            )

            # write entry
            logfile.write(entry + "\n")

            logfile.close()

        if display:
            # Python 3: strings don't need encoding for AddLogText
            self.log.AddLogText(entry + "\n", style)
            print(entry)
        return

    def translateError(self, rawError, context=""):

        rawError = str(rawError)

        # check if it is an API fault payload
        if rawError.rfind("</faultstring>") != -1:
            # Extract faultstring from 500 code and display/log
            rawError = rawError[
                rawError.find("faultstring") + 12 : rawError.rfind("</faultstring")
            ].strip()

        # form friendly error messages for common errors
        if "org.mozilla.javascript" in rawError:
            translatedError = (
                "EQUELLA returned the following script error: "
                + rawError.replace("&quot;", "'")[rawError.find(":") + 1 :].strip()
            )
        elif "Cannot parse server response as XML" in rawError:
            if self.proxy == "":
                translatedError = "Receiving back web page instead of normal response. Check Institution URL."
            else:
                translatedError = "Receiving back web page instead of normal response. Check Institution URL and proxy settings."
        elif "getaddrinfo failed" in rawError:
            if self.proxy == "":
                translatedError = "No response from server. Check Institution URL."
            else:
                translatedError = (
                    "No response from server. Check Institution URL and proxy settings."
                )
        elif "Connection refused" in rawError:
            if self.proxy == "":
                translatedError = "Connection refused by server. Check Institution URL."
            else:
                translatedError = "Connection refused by server. Check Institution URL and proxy settings."
        elif "No service was found" in rawError:
            translatedError = (
                "Supported API was not found. Check EQUELLA version is 4.1 or higher."
            )
        elif "unknown url type" in rawError:
            translatedError = "Unknown URL type. Make certain URL begins with either 'http://' or 'https://'."
        elif "while locating com.tle.beans.entity.itemdef.ItemDefinition" in rawError:
            translatedError = "Collection not found."
        elif "basic auth failed" in rawError:
            translatedError = "Proxy authentication failed. Check proxy settings."
        elif "codec can't decode byte" in rawError:
            translatedError = rawError + ". Try changing encoding."

        else:
            translatedError = rawError
            if rawError.rfind("<html") != -1:
                if context == "login":
                    translatedError = "Receiving back web page instead of normal response. Check Institution URL."
                else:
                    translatedError = (
                        "Receiving back web page instead of normal response."
                    )

        translatedError = translatedError.replace("\\\\", "\\")

        return translatedError

    def group(self, number):
        s = "%d" % number
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ",".join(reversed(groups))

    def validateColumnHeadings(self):
        testPB = PropBagEx("<xml><item/></xml>")
        # iterate through columns and check for validity
        for n, columnHeading in enumerate(self.columnHeadings):
            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA:
                if columnHeading == "":
                    raise Exception(
                        "Blank column heading found on column requiring XPath '%s' (column %s)"
                        % (columnHeading, n + 1)
                    )

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA or (
                self.currentColumns[n][self.COLUMN_DATATYPE]
                in [
                    self.ATTACHMENTLOCATIONS,
                    self.URLS,
                    self.EQUELLARESOURCES,
                    self.CUSTOMATTACHMENTS,
                ]
                and columnHeading.strip() != ""
                and columnHeading.strip()[0] != "#"
            ):
                try:
                    # test xpath
                    testPB.validateXpath(columnHeading.strip())
                except:
                    if self.debug:
                        raise
                    else:
                        exceptionValue = sys.exc_info()[1]
                        scriptErrorMsg = (
                            "Invalid column heading '%s' (column %s). %s"
                            % (columnHeading, n + 1, str(exceptionValue))
                        )
                        raise Exception(scriptErrorMsg)

                # warn the user if any XPaths are attempting to overwrite system nodes
                xpathParts = columnHeading.split("/")
                if columnHeading.strip() == "item" or len(xpathParts) > 1:
                    if columnHeading.strip() == "item" or (
                        xpathParts[0].strip() == "item"
                        and xpathParts[1].strip() in self.itemSystemNodes
                    ):
                        self.echo(
                            "WARNING: XPath '%s' in column %s is writing to a system node"
                            % (columnHeading, n + 1)
                        )

    def getEquellaVersion(self):
        # download and read version.properties
        try:
            versionUrl = self.institutionUrl + "/version.properties"
            versionProperties = ""
            versionProperties = self.tle.getText(versionUrl)
            vpLines = versionProperties.split("\n")

            for line in vpLines:
                line = line.strip()
                lineparts = line.split("=")
                if lineparts[0] == "version.mm":
                    self.eqVersionmm = lineparts[1]
                if lineparts[0] == "version.mmr":
                    self.eqVersionmmr = lineparts[1]
                if lineparts[0] == "version.display":
                    self.eqVersionDisplay = lineparts[1]

        except:
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.echo(
                    "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    )
                )

    def getContributableCollections(self) -> list[str]:
        try:
            # connect to EQUELLA
            self.tle = TLEClient(
                self,
                self.institutionUrl,
                self.username,
                self.password,
                self.proxy,
                self.proxyUsername,
                self.proxyPassword,
                self.debug,
                oauth_client_id=getattr(self, 'oauthClientId', ''),
                oauth_redirect_uri=getattr(self, 'oauthRedirectUri', 'default'),
                settings_manager=getattr(self, 'settingsManager', None),
            )
            self.getEquellaVersion()
        except:
            if self.debug:
                raise
            else:
                raise Exception(self.translateError(str(sys.exc_info()[1]), "login"))

        try:
            # get all accessible collections and their IDs
            itemDefs = self.tle._enumerateItemDefs(forExport=True)

            self.collectionIDs.clear()
            for key, value in itemDefs.items():
                self.collectionIDs[key] = value["uuid"]

            self.tle.logout()

            # return collection names (sorted)
            sorted_collections = sorted(self.collectionIDs.keys())
            print(f"\n=== DEBUG: Final sorted collections list ===")
            print(f"Count: {len(sorted_collections)}")
            print(f"Collections: {sorted_collections}")
            print("=" * 50 + "\n")
            return sorted_collections
        except:
            if self.debug:
                raise
            else:
                raise Exception(self.translateError(str(sys.exc_info()[1])))

    def lookupColumnIndex(self, columnProperty, value):
        """Find index of first column matching the given property and value.

        Returns -1 if not found.
        """
        for index, column in enumerate(self.currentColumns):
            if column[columnProperty] == value:
                return index
        return -1

    def tryPausing(self, message, newline=False):
        progress = message
        if self.pause:
            self.log.Enable()
            # add message to log
            self.log.SetReadOnly(False)
            if newline:
                self.log.AppendText("\n")
            self.log.AppendText(progress)
            self.log.SetReadOnly(True)
            self.log.GotoPos(self.log.GetLength())
            statusOriginalText = self.owner.mainStatusBar.GetStatusText(0)
            self.owner.mainStatusBar.SetStatusText("PAUSED...", 2)

            # pause loop
            count = 0
            while self.pause:
                wx.GetApp().Yield()
                time.sleep(0.5)
                if count == 0:
                    self.owner.mainStatusBar.SetStatusText("PAUSED.", 2)
                    count = 1
                elif count == 1:
                    self.owner.mainStatusBar.SetStatusText("PAUSED..", 2)
                    count = 2
                else:
                    self.owner.mainStatusBar.SetStatusText("PAUSED...", 2)
                    count = 0

            # remove message
            if message != "":
                self.log.DocumentEnd()
                self.log.SetReadOnly(False)
                for i in range(len(progress)):
                    self.log.DeleteBack()
                if newline:
                    self.log.DeleteBack()
                self.log.SetReadOnly(True)
            self.log.Disable()
            self.owner.mainStatusBar.SetStatusText("", 2)

    def runImport(self, owner, testOnly=False):
        self.StopProcessing = False
        self.pause = False
        self.processingStoppedByScript = False

        try:
            # try opening csv file
            if owner.txtCSVPath.GetValue() != "" and not os.path.isdir(
                self.csvFilePath
            ):
                f = open(self.csvFilePath, "rb")
                f.close()
        except:
            owner.mainStatusBar.SetStatusText("Processing halted due to an error", 0)
            raise Exception(
                "CSV file could not be opened, check path: %s" % self.csvFilePath
            )

        # specify folders
        self.logfilespath = os.path.join(
            os.path.dirname(self.csvFilePath), self.logfilesfolder
        )
        self.testItemfolder = os.path.join(
            os.path.dirname(self.csvFilePath), self.testItemfolder
        )
        self.receiptFolder = os.path.join(
            os.path.dirname(self.csvFilePath), self.receiptFolder
        )

        # specify log file name for this run
        if not os.path.exists(self.logfilespath):
            os.makedirs(self.logfilespath)
        self.sessionName = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.logFileName = self.sessionName + ".txt"

        self.echo(self.welcomeLine1, False)
        self.echo(self.welcomeLine2, False)
        if self.debug:
            self.echo("Debug mode on\n", False)

        # create objects for EBI scripts
        self.logger = Logger(self)
        self.process = Process(self)

        self.echo(
            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
            + "Opening a connection to EQUELLA at %s..." % self.institutionUrl
        )

        try:

            # set stats counters
            self.successCount = 0
            self.errorCount = 0

            # connect to EQUELLA
            owner.mainStatusBar.SetStatusText("Connecting...", 0)
            wx.GetApp().Yield()
            self.tle = TLEClient(
                self,
                self.institutionUrl,
                self.username,
                self.password,
                self.proxy,
                self.proxyUsername,
                self.proxyPassword,
                self.debug,
                oauth_client_id=getattr(self, 'oauthClientId', ''),
                oauth_redirect_uri=getattr(self, 'oauthRedirectUri', 'default'),
                settings_manager=getattr(self, 'settingsManager', None),
            )

            # get EQUELLA version
            if self.eqVersionmm == "":
                self.getEquellaVersion()
            versionDisplay = ""
            if self.eqVersionDisplay != "":
                versionDisplay = " (%s)" % self.eqVersionDisplay
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Successfully connected to EQUELLA%s" % versionDisplay
            )

            # Get Collection UUID
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Target collection: '"
                + str(self.collection)
                + "'..."
            )

            # if not previously retreieved get all contributable/searchable collections and their IDs
            if len(self.collectionIDs) == 0:
                itemDefs = self.tle._enumerateItemDefs(forExport=self.export)
                for key, value in itemDefs.items():
                    self.collectionIDs[key] = value["uuid"]

            # get ID of selected collection
            if self.collection in self.collectionIDs.keys():
                itemdefuuid = self.collectionIDs[self.collection]
            else:
                raise Exception(
                    "Collection '" + str(self.collection) + "'" + " not found"
                )

            if hasattr(self.tle, "_ensure_create_privilege_for_collection"):
                self.tle._ensure_create_privilege_for_collection(
                    itemdefuuid, self.collection
                )

            try:
                if not os.path.isdir(self.csvFilePath):
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "Parsing CSV file ("
                        + str(self.csvFilePath)
                        + ")..."
                    )
                else:
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "WARNING: No CSV specified. CSV path is "
                        + str(self.csvFilePath)
                    )

                if not owner.verifyCurrentColumnsMatchCSV():
                    raise Exception(
                        "CSV headings do not match the settings, update the settings to match the CSV column headings"
                    )
                # determine the column indexes for the following column types
                sourceIdentifierColumn = self.lookupColumnIndex(
                    self.COLUMN_SOURCEIDENTIFIER, "YES"
                )
                targetIdentifierColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.TARGETIDENTIFIER
                )
                targetVersionColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.TARGETVERSION
                )
                commandOptionsColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.COMMANDS
                )
                attachmentLocationsColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.ATTACHMENTLOCATIONS
                )
                customAttachmentsColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.CUSTOMATTACHMENTS
                )
                urlsColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.URLS)
                resourcesColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.EQUELLARESOURCES
                )
                itemIdColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.ITEMID)
                versionColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.ITEMVERSION
                )
                thumbnailsColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.THUMBNAILS
                )
                selectedThumbnailColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.SELECTEDTHUMBNAIL
                )
                rowErrorColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.ROWERROR
                )
                collectionColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.COLLECTION
                )
                ownerColumn = self.lookupColumnIndex(self.COLUMN_DATATYPE, self.OWNER)
                collaboratorsColumn = self.lookupColumnIndex(
                    self.COLUMN_DATATYPE, self.COLLABORATORS
                )

                # ignore Source Identifier if column datatype is set to Ignore
                if (
                    sourceIdentifierColumn != -1
                    and self.currentColumns[sourceIdentifierColumn][
                        self.COLUMN_DATATYPE
                    ]
                    == self.IGNORE
                ):
                    sourceIdentifierColumn = -1

                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "DEBUG: rowErrorColumn = %d" % rowErrorColumn
                )

                # parse CSV
                self.csvParse(
                    owner,
                    self.tle,
                    itemdefuuid,
                    testOnly,
                    sourceIdentifierColumn,
                    targetIdentifierColumn,
                    targetVersionColumn,
                    commandOptionsColumn,
                    attachmentLocationsColumn,
                    urlsColumn,
                    resourcesColumn,
                    customAttachmentsColumn,
                    itemIdColumn,
                    versionColumn,
                    rowErrorColumn,
                    collectionColumn,
                    thumbnailsColumn,
                    selectedThumbnailColumn,
                    ownerColumn,
                    collaboratorsColumn,
                )

            except:
                owner.mainStatusBar.SetStatusText(
                    "Processing halted due to an error", 0
                )

                err = str(sys.exc_info()[1])
                exact_error = err

                errorString = ""
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                if self.debug:
                    errorString = "\n" + "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    )

                # check if it is an API fault payload
                if err.rfind("</faultstring>") != -1:
                    # Extract faultstring from 500 code and display/log
                    exact_error = err[
                        err.find("faultstring") + 12 : err.rfind("</faultstring")
                    ]
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "ERROR: "
                    + str(exact_error).strip()
                    + errorString,
                    style=2,
                )

            # close EQUELLA connection
            self.tle.logout()
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Connection successfully closed\n"
            )

        except:
            owner.mainStatusBar.SetStatusText("Processing halted due to an error", 0)

            # could not connect to EQUELLA
            err = str(sys.exc_info()[1])
            exact_error = err

            # form a stack trace for debugging
            errorString = ""
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            if self.debug:
                errorString = "\n" + "".join(
                    str(line)
                    for line in traceback.format_exception(
                        exceptionType, exceptionValue, exceptionTraceback
                    )
                )

            # check if it is an API fault payload
            if err.rfind("</faultstring>") != -1:
                # Extract faultstring from 500 code and display/log
                exact_error = err[
                    err.find("faultstring") + 12 : err.rfind("</faultstring")
                ].strip()

            # create a friendly error message for common connection errors
            exact_error = self.translateError(str(exact_error), "login")

            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "ERROR whilst trying to connect: "
                + str(exact_error).strip()
                + errorString,
                style=2,
            )

        return

    def loadCSV(self, owner=None):
        self.csvArray = []
        if owner == None or owner.txtCSVPath.GetValue() != "":
            if not os.path.isdir(self.csvFilePath):
                encoding = self.encoding
                if encoding.lower() == "utf-8":
                    encoding = "utf-8-sig"
                reader = csv.reader(
                    open(self.csvFilePath, "r", encoding=encoding, newline="")
                )
                for row in reader:
                    self.csvArray.append(row)

        # trim any trailing rows
        for row in reversed(self.csvArray):
            if len(row) > 0:
                break
            else:
                del self.csvArray[-1]

        # if CSV file is empty or non-existent populate the first row with column headings from settings
        if len(self.csvArray) == 0:
            self.csvArray.append([])
            for columnHeading in self.columnHeadings:
                self.csvArray[0].append(columnHeading)

    def csvParse(
        self,
        owner,
        tle,
        itemdefuuid,
        testOnly,
        sourceIdentifierColumn,
        targetIdentifierColumn,
        targetVersionColumn,
        commandOptionsColumn,
        attachmentLocationsColumn,
        urlsColumn,
        resourcesColumn,
        customAttachmentsColumn,
        itemIdColumn,
        versionColumn,
        rowErrorColumn,
        collectionColumn,
        thumbnailsColumn,
        selectedThumbnailColumn,
        ownerColumn,
        collaboratorsColumn,
    ):

        # if real form receipt filename and run check if receipts file is editable
        receiptFilename = ""
        if not self.export:
            if itemIdColumn != -1:
                # form receipts filename
                if owner.txtCSVPath.GetValue() != "" and not os.path.isdir(
                    self.csvFilePath
                ):
                    receiptFilename = os.path.join(
                        self.receiptFolder, os.path.basename(self.csvFilePath)
                    )
                else:
                    receiptFilename = os.path.join(self.receiptFolder, "receipt.csv")

                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "DEBUG: receiptFilename = %s" % receiptFilename
                )

                if os.path.exists(receiptFilename):
                    try:
                        # try opening file for editing
                        f = open(receiptFilename, "wb")
                        f.close()
                    except:
                        raise Exception(
                            "Receipts file cannot be written to and may be in use: %s"
                            % receiptFilename
                        )
        # read the CSV and store the rows in an array
        self.loadCSV(owner)

        # warn if not using attachment metadata targets
        if not self.attachmentMetadataTargets:
            self.echo(
                "\nWARNING: Not using attachments metadata targets (not suitable for EQUELLA 5.0 or higher)\n"
            )

        # calculate absolute appachments basepath for attachments
        self.absoluteAttachmentsBasepath = os.path.join(
            os.path.dirname(self.csvFilePath), self.attachmentsBasepath.strip()
        )
        if self.debug:
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Absolute attachments basepath is "
                + str(self.absoluteAttachmentsBasepath)
            )

        # indicate what scripts, if any, are present
        scriptsPresent = []
        if self.startScript.strip() != "":
            scriptsPresent.append("Start Script")
        if self.preScript.strip() != "":
            scriptsPresent.append("Row Pre-Script")
        if self.postScript.strip() != "":
            scriptsPresent.append("Row Post-Script")
        if self.endScript.strip() != "":
            scriptsPresent.append("End Script")
        if len(scriptsPresent) > 0:
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Scripts present: "
                + ", ".join(scriptsPresent)
            )

        # set variables for scripts
        self.scriptVariables = {}
        if self.export:
            action = 1
        else:
            action = 0

        # run Start Script
        if self.startScript.strip() != "" and not self.export:
            try:
                exec(
                    self.startScript,
                    {
                        "IMPORT": 0,
                        "EXPORT": 1,
                        "mode": action,
                        "vars": self.scriptVariables,
                        "testOnly": testOnly,
                        "institutionUrl": tle.institutionUrl,
                        "collection": self.collection,
                        "csvFilePath": self.csvFilePath,
                        "username": self.username,
                        "logger": self.logger,
                        "columnHeadings": self.columnHeadings,
                        "columnSettings": self.currentColumns,
                        "successCount": self.successCount,
                        "errorCount": self.errorCount,
                        "process": self.process,
                        "basepath": self.absoluteAttachmentsBasepath,
                        "sourceIdentifierIndex": sourceIdentifierColumn,
                        "targetIdentifierIndex": targetIdentifierColumn,
                        "targetVersionIndex": targetVersionColumn,
                        "csvData": self.csvArray,
                        "ebi": self.ebiScriptObject,
                        "equella": tle,
                    },
                )
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(
                        str(line)
                        for line in traceback.format_exception_only(
                            exceptionType, exceptionValue
                        )
                    )[:-1]
                    scriptErrorMsg = (
                        "An error occured in the Start Script:\n%s (line %s)"
                        % (
                            formattedException,
                            traceback.extract_tb(exceptionTraceback)[-1][1],
                        )
                    )
                    raise Exception(scriptErrorMsg)
        if not self.export:
            self.validateColumnHeadings()

        # set all rows to be processed
        scheduledRows = range(1, len(self.csvArray))
        rowsToBeProcessedCount = len(self.csvArray) - 1
        scheduledRowsLabel = "all rows to be processed"

        # check if row filter applies
        if self.rowFilter.strip() != "":
            try:
                scheduledRows = []

                # populate scheduledRows based on rowsFilter
                rowRanges = self.rowFilter.split(",")
                for rowRange in rowRanges:
                    rows = rowRange.split("-")

                    if len(rows) == 1:

                        # single row number encountered
                        scheduledRows.append(int(rows[0]))

                    if len(rows) == 2:

                        # row range provided
                        if rows[1].strip() == "":

                            # no finish row so assume all remaining rows (e.g. "5-")
                            rows[1] = len(self.csvArray) - 1

                        scheduledRows.extend(range(int(rows[0]), int(rows[1]) + 1))

                # remove any duplicates (preserving order)
                scheduledRows = Utils.removeDuplicates(scheduledRows)

                # determine how many rows to be processed
                rowsToBeProcessedCount = 0
                for rc in scheduledRows:
                    if rc < len(self.csvArray):
                        rowsToBeProcessedCount += 1

                # form label for how many rows to be processed
                scheduledRowsLabel = "%s to be processed [%s]" % (
                    rowsToBeProcessedCount,
                    self.rowFilter,
                )

            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    self.echo(
                        "".join(
                            str(line)
                            for line in traceback.format_exception(
                                exceptionType, exceptionValue, exceptionTraceback
                            )
                        )
                    )
                raise Exception("Invalid row filter specified")
        if not self.export:
            # echo rows to be processed
            if testOnly:
                actionString = "%s row(s) found, %s (test only)" % (
                    len(self.csvArray) - 1 if len(self.csvArray) > 0 else 0,
                    scheduledRowsLabel,
                )
            else:
                actionString = "%s row(s) found, %s" % (
                    len(self.csvArray) - 1 if len(self.csvArray) > 0 else 0,
                    scheduledRowsLabel,
                )
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString
            )

            # echo draft and new version settings
            actionString = ""
            if sourceIdentifierColumn != -1 or targetIdentifierColumn != -1:
                if self.saveAsDraft and self.createNewVersions:
                    actionString = "Options -> Create new versions of existing items in draft status"
                elif self.createNewVersions:
                    actionString = "Options -> Create new versions of existing items"
                elif self.saveAsDraft:
                    actionString = "Options -> Create new items in draft status (status of existing items will remain unchanged)"
            elif self.saveAsDraft:
                actionString = "Options -> Create items in draft status"
            if actionString != "":
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + actionString
                )

            # echo append/replace metadata settings
            actionString = ""
            if sourceIdentifierColumn != -1 or targetIdentifierColumn != -1:
                if self.existingMetadataMode == self.APPENDMETA:
                    actionString = "Options -> Append metadata to existing items"
                if self.existingMetadataMode == self.REPLACEMETA:
                    actionString = (
                        "Options -> Replace specified metadata in existing items"
                    )
                if actionString != "":
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + actionString
                    )

                # echo append attachment settings
                if self.appendAttachments:
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "Options -> Append attachments to existing items"
                    )

        # iterate through the rows of metadata from the CSV file creating an item in EQUELLA for each
        rowReceipts = {}
        processedCounter = 0
        self.sourceIdentifierReceipts = {}

        self.owner.progressGauge.SetRange(len(scheduledRows))
        self.owner.progressGauge.SetValue(processedCounter)
        self.owner.progressGauge.Show()

        if not self.export:

            # if Collection column spectifed check that all collection names resolve to collectionIDs
            if collectionColumn != -1:
                for rowCounter in scheduledRows:
                    collectionName = self.csvArray[rowCounter][collectionColumn]
                    if (
                        collectionName.strip() != ""
                        and collectionName not in self.collectionIDs.keys()
                    ):
                        raise Exception(
                            "Unknown collection '%s' at row %s"
                            % (collectionName, rowCounter)
                        )

            rowCounter = 0
            for rowCounter in scheduledRows:
                if self.StopProcessing:
                    break

                if rowCounter < len(self.csvArray):
                    self.Skip = False
                    processedCounter += 1

                    self.echo("---")

                    self.tryPausing("[Paused]")

                    # update UI and log
                    wx.GetApp().Yield()
                    owner.mainStatusBar.SetStatusText(
                        "Processing row %s [%s of %s]"
                        % (rowCounter, processedCounter, rowsToBeProcessedCount),
                        0,
                    )

                    action = "Processing item..."
                    if testOnly:
                        action = "Validating item..."
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + " Row %s [%s of %s]: %s"
                        % (rowCounter, processedCounter, rowsToBeProcessedCount, action)
                    )

                    # process row
                    (
                        savedItemID,
                        savedItemVersion,
                        sourceIdentifier,
                        rowData,
                        rowError,
                    ) = self.processRow(
                        rowCounter,
                        self.csvArray[rowCounter],
                        self.tle,
                        itemdefuuid,
                        self.collectionIDs,
                        testOnly,
                        sourceIdentifierColumn,
                        targetIdentifierColumn,
                        targetVersionColumn,
                        commandOptionsColumn,
                        attachmentLocationsColumn,
                        urlsColumn,
                        resourcesColumn,
                        customAttachmentsColumn,
                        collectionColumn,
                        thumbnailsColumn,
                        selectedThumbnailColumn,
                        ownerColumn,
                        collaboratorsColumn,
                        rowErrorColumn,
                    )

                    # add to row receipts
                    rowReceipts[rowCounter] = (savedItemID, savedItemVersion)
                    if sourceIdentifierColumn != -1:
                        self.sourceIdentifierReceipts[sourceIdentifier] = (
                            savedItemID,
                            savedItemVersion,
                        )

                    # update row in CSV array for receipt and script-processed row data
                    if itemIdColumn != -1:
                        # assign itemID to receipt cell
                        rowData[itemIdColumn] = savedItemID
                        rowData[versionColumn] = str(savedItemVersion)

                    # update row error column if it exists (independent of itemIdColumn)
                    if rowErrorColumn != -1:
                        self.echo(
                            "  DEBUG: rowData length = %d, rowErrorColumn = %d"
                            % (len(rowData), rowErrorColumn)
                        )
                        if rowErrorColumn < len(rowData):
                            rowData[rowErrorColumn] = rowError
                        else:
                            # Extend rowData if necessary
                            while len(rowData) <= rowErrorColumn:
                                rowData.append("")
                            rowData[rowErrorColumn] = rowError
                            self.echo(
                                "  DEBUG: Extended rowData to length %d" % len(rowData)
                            )

                        if rowError != "":
                            self.echo("  Row error captured: %s" % rowError)
                            self.echo(
                                "  DEBUG: Storing error at index %d in rowData"
                                % rowErrorColumn
                            )
                            self.echo(
                                "  DEBUG: rowData[%d] = %s"
                                % (rowErrorColumn, rowData[rowErrorColumn])
                            )
                            self.echo(
                                "  DEBUG: csvArray[%d][%d] = %s"
                                % (
                                    rowCounter,
                                    rowErrorColumn,
                                    self.csvArray[rowCounter][rowErrorColumn],
                                )
                            )
                    else:
                        self.echo("  DEBUG: rowErrorColumn is -1, error not stored")

                    # always update the csvArray with potentially modified rowData
                    self.csvArray[rowCounter] = rowData

                    # update progress bar
                    self.owner.progressGauge.SetValue(processedCounter)

            if self.StopProcessing:
                self.echo("---")
                if self.processingStoppedByScript:
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "Processing halted"
                    )
                else:
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "Processing halted by user"
                    )

            self.echo("---")

            # run End Script
            if self.endScript.strip() != "":
                try:
                    exec(
                        self.endScript,
                        {
                            "IMPORT": 0,
                            "EXPORT": 1,
                            "mode": action,
                            "vars": self.scriptVariables,
                            "rowCounter": rowCounter,
                            "testOnly": testOnly,
                            "institutionUrl": tle.institutionUrl,
                            "collection": self.collection,
                            "csvFilePath": self.csvFilePath,
                            "username": self.username,
                            "logger": self.logger,
                            "columnHeadings": self.columnHeadings,
                            "columnSettings": self.currentColumns,
                            "successCount": self.successCount,
                            "errorCount": self.errorCount,
                            "process": self.process,
                            "basepath": self.absoluteAttachmentsBasepath,
                            "sourceIdentifierIndex": sourceIdentifierColumn,
                            "targetIdentifierIndex": targetIdentifierColumn,
                            "targetVersionIndex": targetVersionColumn,
                            "csvData": self.csvArray,
                            "ebi": self.ebiScriptObject,
                            "equella": tle,
                        },
                    )
                except:
                    if self.debug:
                        exceptionType, exceptionValue, exceptionTraceback = (
                            sys.exc_info()
                        )
                        scriptErrorMsg = (
                            "An error occured in the End Script:\n"
                            + "".join(
                                str(line)
                                for line in traceback.format_exception(
                                    exceptionType, exceptionValue, exceptionTraceback
                                )
                            )
                        )
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + scriptErrorMsg,
                            style=2,
                        )
                    else:
                        exceptionType, exceptionValue, exceptionTraceback = (
                            sys.exc_info()
                        )
                        formattedException = "".join(
                            str(line)
                            for line in traceback.format_exception_only(
                                exceptionType, exceptionValue
                            )
                        )[:-1]
                        scriptErrorMsg = (
                            "An error occured in the End Script:\n%s (line %s)"
                            % (
                                formattedException,
                                traceback.extract_tb(exceptionTraceback)[-1][1],
                            )
                        )
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + scriptErrorMsg,
                            style=2,
                        )

            # output receipts if Item ID column specified or Row Error column specified, and real run
            if itemIdColumn != -1 or rowErrorColumn != -1:

                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "Writing receipts file..."
                )
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "DEBUG: Writing to %s" % receiptFilename
                )

                # create receipts folder if one doesn't exist
                if not os.path.exists(self.receiptFolder):
                    os.makedirs(self.receiptFolder)

                # open csv writer and output orginal csv rows using self.columnHeadings as first row (instead of first row of self.csvArray)
                f = open(receiptFilename, "w", encoding=self.encoding, newline="")
                writer = csv.writer(f)
                writer.writerow(list(self.columnHeadings))
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "DEBUG: Writing header row with %d columns"
                    % len(self.columnHeadings)
                )
                for i in range(1, len(self.csvArray)):
                    row_to_write = list(self.csvArray[i])
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "DEBUG: Writing row %d with %d columns: %s"
                        % (i, len(row_to_write), str(row_to_write))
                    )
                    writer.writerow(row_to_write)
                f.close()
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "DEBUG: Receipt file closed"
                )

        else:
            # export
            actionString = ""
            if sourceIdentifierColumn == -1 and targetIdentifierColumn == -1:
                if self.includeNonLive:
                    actionString = "Options -> Include non-live items in export"
            if actionString != "":
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + actionString
                )

            self.exportedFiles = []
            self.exportCSV(
                owner,
                self.tle,
                itemdefuuid,
                self.collectionIDs,
                testOnly,
                scheduledRows,
                sourceIdentifierColumn,
                targetIdentifierColumn,
                targetVersionColumn,
                commandOptionsColumn,
                attachmentLocationsColumn,
                collectionColumn,
                rowsToBeProcessedCount,
            )

        # form outcome report
        errorReport = ""
        if self.errorCount > 0:
            errorReport = " errors: %s" % (self.errorCount)
        resultReport = "Processing complete (success: %s%s)" % (
            self.successCount,
            errorReport,
        )

        self.echo(
            time.strftime("%H:%M:%S: ", time.localtime(time.time())) + resultReport
        )

        owner.mainStatusBar.SetStatusText(resultReport, 0)

        # Write back to original CSV file if Row Error column exists or if not in test mode
        if (not testOnly or rowErrorColumn != -1) and not os.path.isdir(
            self.csvFilePath
        ):
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Writing CSV file back to: %s" % self.csvFilePath
            )
            with open(self.csvFilePath, "w", encoding=self.encoding, newline="") as f:
                writer = csv.writer(f)
                writer.writerows(self.csvArray)
                f.flush()
                os.fsync(f.fileno())
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "CSV file updated successfully"
            )

    # getEquellaResourceDetail() retrieves an item or item attachment details necessary for forming an EQUELLA resource-type attachment
    def getEquellaResourceDetail(
        self,
        resourceUrl,
        itemdefuuid,
        collectionIDs,
        sourceIdentifierColumn,
        isCalHolding,
    ):

        # break up resource url
        resourceUrlParts = []
        if resourceUrl[0] == "[" or resourceUrl[0] == "{":
            if resourceUrl[-1] == "}":
                resourceUrlParts.append(resourceUrl)
            elif resourceUrl[-2:-1] == "}/":
                resourceUrlParts.append(resourceUrl[:-1])
            else:
                resourceUrlParts.append(resourceUrl.split("}/")[0] + "}")
                resourceUrlParts += resourceUrl.split("}/")[1].split("/")
        else:
            resourceUrlParts = resourceUrl.split("/")

        # get item UUID
        resourceItemUuid = resourceUrlParts[0]

        # check if itemUUID is actually a sourceIdentifier
        # format is {<source identifier>} or [<collection name>]{<source identifier>} or [<collection name>||<source identifier xpath>]{<source identifier>}
        collection = ""
        sourceIdentifier = ""
        sourceIdentifierXpath = ""

        # no collection specified so use same collection as item
        if resourceItemUuid[0] == "{" and resourceItemUuid[-1] == "}":
            sourceIdentifier = resourceItemUuid[1:-1]

        # collection specified so resolve to colleciton ID and use that
        if resourceItemUuid[0] == "[" and resourceItemUuid[-1] == "}":
            collSplitPoint = resourceItemUuid.find("]{")
            if collSplitPoint != -1:
                sourceIdentifier = resourceItemUuid[collSplitPoint + 2 : -1]
                collection = resourceItemUuid[1:collSplitPoint]

                # extract an xpath and a source identifier xpath (if one supplied)
                collectionParts = collection.split("][")
                collection = collectionParts[0]
                if len(collectionParts) == 2:
                    sourceIdentifierXpath = collectionParts[1]

                # get collection ID for collection
                if collection in collectionIDs:
                    itemdefuuid = collectionIDs[collection]
                else:
                    raise Exception(
                        "Collection specified not found: " + str(collection)
                    )
        # if source identifer (and optionally collection) specified then find resource by that
        if sourceIdentifier != "":

            # first try checking any source identifiers that were processed in the run
            if collection == "" and sourceIdentifier in self.sourceIdentifierReceipts:
                resourceItemUuid = self.sourceIdentifierReceipts[sourceIdentifier][0]

            # if source identifer not processed in this run then look it up in EQUELLA
            else:
                if self.debug:
                    self.echo("    Source identifier = " + sourceIdentifier)

                if sourceIdentifierXpath == "":
                    if sourceIdentifierColumn != -1:

                        # determine source identifier xpath if not specified in resource URL
                        sourceIdentifierXpath = (
                            "/xml/" + self.columnHeadings[sourceIdentifierColumn]
                        )

                    else:
                        raise Exception("No source identifier specified.")
                searchFilter = sourceIdentifierXpath + "='" + sourceIdentifier + "'"
                results = self.tle.search(
                    0, 10, "/item/name", [itemdefuuid], searchFilter, query=""
                )

                # if any matches get first matching item for editing
                if int(results.getNode("available")) > 0:
                    resourceItemUuid = results.getNode("result/xml/item/@id")
                    if self.debug:
                        self.echo(
                            "  Resource item found by source identifier = '%s' in collectionID = '%s' (%s)"
                            % (sourceIdentifier, itemdefuuid, resourceItemUuid)
                        )
                else:
                    raise Exception(
                        "Item not found with source identifier '%s'" % sourceIdentifier
                    )
        # get item version
        if len(resourceUrlParts) == 1:
            resourceItemVersion = 0
        elif resourceUrlParts[1] == "":
            resourceItemVersion = 0
        else:
            resourceItemVersion = int(resourceUrlParts[1])

        # get attachment path if any
        attachmentPath = ""
        if len(resourceUrlParts) > 2:
            attachmentPath = "/".join(resourceUrlParts[2:])

        # retrieve item XML and get attachment UUID and description
        resourceXml = self.tle.getItem(resourceItemUuid, resourceItemVersion)
        resourceAttachmentUuid = ""
        if attachmentPath == "":
            # resource is item itself
            resourceName = resourceXml.getNode("item/name")

            # if resource is CAL holding then use explicit item version
            if isCalHolding:
                resourceItemVersion = resourceXml.getNode("item/@version")
        else:
            if attachmentPath.upper() == "<PACKAGE>":
                # get package details
                # try for SCORM package
                for attachmentSubtree in resourceXml.iterate(
                    "item/attachments/attachment"
                ):
                    if (
                        attachmentSubtree.getNode("@type") == "custom"
                        and attachmentSubtree.getNode("type") == "scorm"
                    ):
                        resourceAttachmentUuid = attachmentSubtree.getNode("uuid")
                        resourceName = attachmentSubtree.getNode("description")
                        break
                if resourceAttachmentUuid == None or resourceAttachmentUuid == "":
                    # no SCORM package so try for IMS package
                    resourceAttachmentUuid = resourceXml.getNode(
                        "item/itembody/packagefile/@uuid"
                    )
                    resourceName = resourceXml.getNode("item/itembody/packagefile")
                    if resourceAttachmentUuid == None:
                        raise Exception(
                            "package not found in item %s/%s"
                            % (resourceItemUuid, resourceItemVersion)
                        )
            else:
                # resource is a file/url attachment
                for attachmentSubtree in resourceXml.iterate(
                    "item/attachments/attachment"
                ):
                    if attachmentSubtree.getNode("file") == attachmentPath:
                        resourceAttachmentUuid = attachmentSubtree.getNode("uuid")
                        resourceName = attachmentSubtree.getNode("description")
                        break
                if resourceAttachmentUuid == "":
                    raise Exception(
                        "%s not found in item %s/%s"
                        % (attachmentPath, resourceItemUuid, resourceItemVersion)
                    )

        return (
            resourceItemUuid,
            resourceItemVersion,
            resourceAttachmentUuid,
            resourceName,
        )

    # addCALRelations() adds CAL holding relations to a CAL portion item
    def addCALRelations(self, holdingMetadataTarget, itemXml):
        holdingAttachmentUUIDs = itemXml.getNodes(holdingMetadataTarget)
        if len(holdingAttachmentUUIDs) > 0:
            holdingAttachmentFound = False
            for attachment in itemXml.iterate("item/attachments/attachment"):
                if attachment.getNode("uuid") == holdingAttachmentUUIDs[0]:
                    relation = itemXml.newSubtree("item/relations/targets/relation")
                    relation.createNode("@resource", attachment.getNode("uuid"))
                    relation.createNode("@type", "CAL_HOLDING")
                    relationitem = relation.newSubtree("item")
                    relationitem.createNode("name", attachment.getNode("description"))

                    holdingUuid = ""
                    holdingVersion = ""
                    for attachmentAttribute in attachment.iterate("attributes/entry"):
                        entryName = attachmentAttribute.getNode("string")
                        if entryName == "uuid":
                            holdingUuid = attachmentAttribute.getNodes("string")[1]
                        if entryName == "version":
                            holdingVersion = attachmentAttribute.getNode("int")

                    relationitem.createNode("@uuid", holdingUuid)
                    relationitem.createNode("@version", holdingVersion)
                    holdingAttachmentFound = True
                    break
            if not holdingAttachmentFound:
                raise Exception("No holding item attached to this portion")
        else:
            raise Exception(
                "No metadata targets for holding items found in this portion"
            )

    def _processUnzipAttachment(
        self,
        item,
        filename,
        filepath,
        filesize,
        attachmentLinkName,
        uploadStatus,
        n,
        zfobj,
        testOnly,
        columnHeading=None,
    ):
        """Process UNZIP command: upload zip, unzip on server, add extracted files as attachments with ZIP_ATTACHMENT_UUID references.

        Expected format for attachment names: (("file1.pdf", "Description 1"), ("file2.pdf", "Description 2"))
        Special format "*" includes all files in zip.
        Original zip file is always added as the first attachment.
        """
        self.echo("    Unzip file")
        if not testOnly:
            attemptingUpload = True
            item.attachFile(
                "_zips/" + filename,
                Utils.openFileForReading(filepath),
                uploadStatus,
                self.chunkSize,
            )
            if self.StopProcessing:
                return
            attemptingUpload = False
            wx.GetApp().Yield()
            item.unzipFile("_zips/" + filename, filename)

        if attachmentLinkName != "":
            try:
                startPagesListAsString = '(("#####","#####"),' + attachmentLinkName[1:]
                exec_dict = {}
                exec("startPagesList = " + startPagesListAsString, exec_dict)
                startPagesList = exec_dict["startPagesList"]
            except Exception:
                raise Exception(
                    "List of links to unzipped files incorrectly formatted."
                )

            parentZipAttachmentUUID = str(uuid.uuid4())

            zipAttachmentUUID = str(uuid.uuid4())
            item.addStartPage(
                filename, "_zips/" + filename, filesize, zipAttachmentUUID
            )

            if self.attachmentMetadataTargets and columnHeading:
                item.getXml().createNode(columnHeading, zipAttachmentUUID)

            startPagesDict = {}
            for startPage in startPagesList:
                if startPage[0] != "#####":
                    startPagesDict[startPage[0]] = startPage[1]

            for startPage in startPagesList:
                if startPage[0] == filename:
                    pass
                elif startPage[0] == "*":
                    for archiveFile in zfobj.namelist():
                        if (
                            (archiveFile not in startPagesDict)
                            and (archiveFile != filename)
                            and not archiveFile.endswith("/")
                        ):
                            archiveFilesize = zfobj.getinfo(archiveFile).file_size
                            attachmentUUID = str(uuid.uuid4())
                            item.addStartPageWithZipAttribute(
                                os.path.basename(archiveFile),
                                filename + "/" + archiveFile,
                                archiveFilesize,
                                attachmentUUID,
                                parentZipAttachmentUUID,
                            )
                            if self.attachmentMetadataTargets and columnHeading:
                                item.getXml().createNode(columnHeading, attachmentUUID)

    def processRow(
        self,
        rowCounter,
        meta,
        tle,
        itemdefuuid,
        collectionIDs,
        testOnly,
        sourceIdentifierColumn,
        targetIdentifierColumn,
        targetVersionColumn,
        commandOptionsColumn,
        attachmentLocationsColumn,
        urlsColumn,
        resourcesColumn,
        customAttachmentsColumn,
        collectionColumn,
        thumbnailsColumn,
        selectedThumbnailColumn,
        ownerColumn,
        collaboratorsColumn,
        rowErrorColumn,
    ):
        """Create or update a single item in EQUELLA from a CSV row.
        Delegates the heavy lifting to the RowProcessor class.
        """
        processor = RowProcessor(self)
        return processor.processRow(
            rowCounter,
            meta,
            tle,
            itemdefuuid,
            collectionIDs,
            testOnly,
            sourceIdentifierColumn,
            targetIdentifierColumn,
            targetVersionColumn,
            commandOptionsColumn,
            attachmentLocationsColumn,
            urlsColumn,
            resourcesColumn,
            customAttachmentsColumn,
            collectionColumn,
            thumbnailsColumn,
            selectedThumbnailColumn,
            ownerColumn,
            collaboratorsColumn,
            rowErrorColumn,
        )

    def exportCSV(
        self,
        owner,
        tle,
        itemdefuuid,
        collectionIDs,
        testOnly,
        scheduledRows,
        sourceIdentifierColumn,
        targetIdentifierColumn,
        targetVersionColumn,
        commandOptionsColumn,
        attachmentLocationsColumn,
        collectionColumn,
        rowsToBeProcessedCount,
    ):

        if not testOnly:
            if owner.txtCSVPath.GetValue() != "" and not os.path.isdir(
                self.csvFilePath
            ):
                try:
                    # test opening file for writing (append test only)

                    f = open(self.csvFilePath, "a", encoding="utf-8")
                    f.close()
                except:
                    raise Exception(
                        "CSV cannot be written to and may be in use: %s"
                        % self.csvFilePath
                    )
        allRowsError = False
        self.successCount = 0
        self.errorCount = 0
        processedCounter = 0

        # run Start Script
        if self.startScript.strip() != "":
            try:
                exec(
                    self.startScript,
                    {
                        "IMPORT": 0,
                        "EXPORT": 1,
                        "mode": 1,
                        "vars": self.scriptVariables,
                        "testOnly": testOnly,
                        "institutionUrl": tle.institutionUrl,
                        "collection": self.collection,
                        "csvFilePath": self.csvFilePath,
                        "username": self.username,
                        "logger": self.logger,
                        "columnHeadings": self.columnHeadings,
                        "columnSettings": self.currentColumns,
                        "successCount": self.successCount,
                        "errorCount": self.errorCount,
                        "process": self.process,
                        "basepath": self.absoluteAttachmentsBasepath,
                        "sourceIdentifierIndex": sourceIdentifierColumn,
                        "targetIdentifierIndex": targetIdentifierColumn,
                        "targetVersionIndex": targetVersionColumn,
                        "csvData": self.csvArray,
                        "ebi": self.ebiScriptObject,
                        "equella": tle,
                    },
                )
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(
                        str(line)
                        for line in traceback.format_exception_only(
                            exceptionType, exceptionValue
                        )
                    )[:-1]
                    scriptErrorMsg = (
                        "An error occured in the Start Script:\n%s (line %s)"
                        % (
                            formattedException,
                            traceback.extract_tb(exceptionTraceback)[-1][1],
                        )
                    )
                    raise Exception(scriptErrorMsg)
        # check column headings
        self.validateColumnHeadings()

        actionString = ""
        if self.includeNonLive:
            actionString = "Options -> Export non-live items"
        if actionString != "":
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString
            )

        if sourceIdentifierColumn == -1 and targetIdentifierColumn == -1:

            # WHERE Clause
            if self.whereClause.strip() != "":
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "WHERE Clause: %s" % self.whereClause
                )

            # determine which collection to search (seach all collections if Collections column present)
            if collectionColumn == -1:
                collectionsToSearch = [itemdefuuid]
            else:
                collectionsToSearch = []

            # get available
            try:
                searchResults = tle.search(
                    query="",
                    itemdefs=collectionsToSearch,
                    where=self.whereClause.strip(),
                    onlyLive=not self.includeNonLive,
                    orderType=0,
                    reverseOrder=False,
                    offset=0,
                    limit=1,
                )

            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    errorString = (
                        "\n"
                        + "".join(
                            str(line)
                            for line in traceback.format_exception(
                                exceptionType, exceptionValue, exceptionTraceback
                            )
                        )
                        + "\n"
                    )
                else:
                    errorString = "Error whist attempting to search: " + str(
                        sys.exc_info()[1]
                    )
                raise Exception(str(errorString))
            rowCounter = 0
            available = int(searchResults.getNode("available"))
            pageSize = 50

            # determine how many rows to be processed
            itemsToBeProcessedCount = available
            if self.rowFilter.strip() != "":
                itemsToBeProcessedCount = 0
                for rc in scheduledRows:
                    if rc <= available:
                        itemsToBeProcessedCount += 1

            # echo rows to be processed
            scheduledRowsLabel = " "
            if itemsToBeProcessedCount > 0:
                scheduledRowsLabel = ", all to be exported "
            if self.rowFilter != "":
                scheduledRowsLabel = ", %s to be processed [%s] " % (
                    itemsToBeProcessedCount,
                    self.rowFilter,
                )
            if testOnly:
                actionString = "%s item(s) found%s(test only)" % (
                    available,
                    scheduledRowsLabel,
                )
            else:
                actionString = "%s item(s) found%s" % (available, scheduledRowsLabel)
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString
            )

            self.owner.progressGauge.SetRange(itemsToBeProcessedCount)
            self.owner.progressGauge.SetValue(processedCounter)
            self.owner.progressGauge.Show()

            # crop list down to first row
            self.csvArray = self.csvArray[:1]

            # outer loop of "pages" of pageSize
            pagesRequired = available // pageSize + 1
            offset = 0
            lastScheduledItem = -1
            if len(scheduledRows) > 0:
                lastScheduledItem = max(scheduledRows)

            for pageCounter in range(1, pagesRequired + 1):

                searchResults = tle.search(
                    query="",
                    itemdefs=collectionsToSearch,
                    where=self.whereClause.strip(),
                    onlyLive=not self.includeNonLive,
                    orderType=0,
                    reverseOrder=False,
                    offset=offset,
                    limit=pageSize,
                )

                wx.GetApp().Yield()

                for result in searchResults.iterate("result"):
                    if not self.StopProcessing:
                        try:

                            # increment rowCounter
                            rowCounter += 1

                            self.Skip = False

                            if (
                                self.rowFilter.strip() == ""
                                or rowCounter in scheduledRows
                            ):

                                processedCounter += 1

                                self.echo("---")

                                itemXml = result.getSubtree("xml")
                                itemID = itemXml.getNode("item/@id")
                                itemVersion = itemXml.getNode("item/@version")

                                # update UI and log
                                owner.mainStatusBar.SetStatusText(
                                    "Exporting item %s [%s of %s]"
                                    % (
                                        rowCounter,
                                        processedCounter,
                                        itemsToBeProcessedCount,
                                    ),
                                    0,
                                )
                                self.owner.progressGauge.SetValue(processedCounter)
                                if testOnly:
                                    action = "Exporting item %s/%s (test only)..." % (
                                        itemID,
                                        itemVersion,
                                    )
                                else:
                                    action = "Exporting item %s/%s..." % (
                                        itemID,
                                        itemVersion,
                                    )

                                self.echo(
                                    time.strftime(
                                        "%H:%M:%S: ", time.localtime(time.time())
                                    )
                                    + " Item %s [%s of %s]: %s"
                                    % (
                                        rowCounter,
                                        processedCounter,
                                        itemsToBeProcessedCount,
                                        action,
                                    )
                                )
                                wx.GetApp().Yield()

                                rowData = self.exportItem(
                                    rowCounter,
                                    itemXml,
                                    tle,
                                    itemdefuuid,
                                    testOnly,
                                    sourceIdentifierColumn,
                                    targetIdentifierColumn,
                                    targetVersionColumn,
                                    commandOptionsColumn,
                                    attachmentLocationsColumn,
                                    collectionIDs,
                                    self.csvArray,
                                )

                                if not self.Skip:
                                    if len(self.csvArray) > rowCounter:
                                        self.csvArray[rowCounter] = rowData
                                    else:
                                        self.csvArray.append(rowData)
                                    self.successCount += 1

                            if (
                                self.rowFilter.strip() != ""
                                and rowCounter == lastScheduledItem
                            ):
                                break
                            offset = rowCounter

                        except:
                            exactError = str(sys.exc_info()[1])
                            self.errorCount += 1

                            # form error string for debugging
                            errorDebug = ""
                            if self.debug:
                                exceptionType, exceptionValue, exceptionTraceback = (
                                    sys.exc_info()
                                )
                                errorDebug = "\n" + "".join(
                                    str(line)
                                    for line in traceback.format_exception(
                                        exceptionType,
                                        exceptionValue,
                                        exceptionTraceback,
                                    )
                                )

                            exactError = self.translateError(str(exactError))
                            self.echo(
                                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                                + "ERROR: %s%s" % (str(exactError), str(errorDebug)),
                                style=2,
                            )

                            # halt processing if the error will apply to all rows
                            if allRowsError:
                                raise Exception("Halting process")
                    # stop processing
                    else:
                        break
                if self.StopProcessing:
                    self.echo("---")
                    if self.processingStoppedByScript:
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + "Export halted"
                        )
                    else:
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + "Export halted by user"
                        )
                    break
                elif self.rowFilter.strip() != "" and rowCounter == lastScheduledItem:
                    break
        else:

            # echo rows to be processed
            scheduledRowsLabel = "all to be exported"
            if self.rowFilter != "":
                scheduledRowsLabel = "%s to be processed [%s]" % (
                    rowsToBeProcessedCount,
                    self.rowFilter,
                )
            if testOnly:
                actionString = str(
                    len(self.csvArray) - 1
                ) + " row(s) found, %s (test only)" % (scheduledRowsLabel)
            else:
                actionString = str(len(self.csvArray) - 1) + " row(s) found, %s" % (
                    scheduledRowsLabel
                )
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time())) + actionString
            )

            self.owner.progressGauge.SetRange(rowsToBeProcessedCount)
            self.owner.progressGauge.SetValue(processedCounter)
            self.owner.progressGauge.Show()

            # iterate through the rows of metadata from the CSV file exporting an item from EQUELLA for each
            for rowCounter in scheduledRows:

                if not self.StopProcessing and rowCounter < len(self.csvArray):
                    try:
                        processedCounter += 1
                        self.Skip = False

                        self.echo("---")

                        # update UI and log
                        owner.mainStatusBar.SetStatusText(
                            "Exporting row %s [%s of %s]"
                            % (rowCounter, processedCounter, rowsToBeProcessedCount),
                            0,
                        )
                        self.owner.progressGauge.SetValue(processedCounter)
                        if testOnly:
                            action = "Exporting item (test only)..."
                        else:
                            action = "Exporting item..."
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + " Row %s [%s of %s]: %s"
                            % (
                                rowCounter,
                                processedCounter,
                                rowsToBeProcessedCount,
                                action,
                            )
                        )
                        wx.GetApp().Yield()

                        rowitemdefuuid = itemdefuuid
                        # override the collection ID if one has been specified in the row
                        if collectionColumn != -1:
                            collectionName = self.csvArray[rowCounter][
                                collectionColumn
                            ].strip()
                            if collectionName != "":
                                if collectionName in collectionIDs:
                                    rowitemdefuuid = collectionIDs[collectionName]
                                    self.echo(
                                        "  Source collection: '%s'" % collectionName
                                    )
                                else:
                                    raise Exception(
                                        "'"
                                        + str(collectionName)
                                        + "' collection not found"
                                    )
                        itemFound = False

                        # get targeted item version if target version specified
                        itemVersion = 0
                        if (
                            targetVersionColumn != -1
                            and self.csvArray[rowCounter][targetVersionColumn].strip()
                            != ""
                        ):
                            try:
                                itemVersion = int(
                                    self.csvArray[rowCounter][
                                        targetVersionColumn
                                    ].strip()
                                )
                                if itemVersion < -1:
                                    raise Exception("Invalid item version specified")
                            except:
                                raise Exception("Invalid item version specified")
                        # if Source Identifier column specified check if item exists by sourceIdentifier
                        if sourceIdentifierColumn != -1:
                            if (
                                self.csvArray[rowCounter][
                                    sourceIdentifierColumn
                                ].strip()
                                != ""
                            ):
                                if (
                                    targetVersionColumn == -1
                                    or self.csvArray[rowCounter][
                                        targetVersionColumn
                                    ].strip()
                                    == ""
                                ):
                                    noVersionSpecified = True
                                else:
                                    noVersionSpecified = False

                                # determine if items versions of any status need to be returned
                                if itemVersion != 0 or (
                                    self.includeNonLive and noVersionSpecified
                                ):
                                    onlyLive = False
                                    limit = 50
                                else:
                                    onlyLive = True
                                    limit = 1

                                sourceIdentifier = self.csvArray[rowCounter][
                                    sourceIdentifierColumn
                                ].strip()
                                self.echo("  Source identifier = " + sourceIdentifier)
                                if (
                                    targetVersionColumn != -1
                                    and self.csvArray[rowCounter][
                                        targetVersionColumn
                                    ].strip()
                                    != ""
                                ):
                                    self.echo(
                                        "  Target version = "
                                        + self.csvArray[rowCounter][
                                            targetVersionColumn
                                        ].strip()
                                    )
                                searchFilter = (
                                    "/xml/"
                                    + self.columnHeadings[sourceIdentifierColumn]
                                    + "='"
                                    + sourceIdentifier
                                    + "'"
                                )
                                results = tle.search(
                                    0,
                                    limit,
                                    "",
                                    [rowitemdefuuid],
                                    searchFilter,
                                    query="",
                                    onlyLive=onlyLive,
                                )

                                # if any matches get first matching item for editing
                                if int(results.getNode("available")) > 0:
                                    if itemVersion == 0 and not (
                                        self.includeNonLive and noVersionSpecified
                                    ):
                                        # get first live version
                                        itemXml = results.getSubtree("result/xml")
                                        itemID = results.getNode("result/xml/item/@id")
                                        itemVersion = results.getNode(
                                            "result/xml/item/@version"
                                        )
                                        itemFound = True
                                    else:
                                        if itemVersion > 0:
                                            # find item by item version
                                            for itemResult in results.iterate("result"):
                                                if itemResult.getNode(
                                                    "xml/item/@version"
                                                ) == str(itemVersion):
                                                    itemXml = itemResult.getSubtree(
                                                        "xml"
                                                    )
                                                    itemID = itemResult.getNode(
                                                        "xml/item/@id"
                                                    )
                                                    itemFound = True
                                                    break
                                            if not itemFound:
                                                self.echo("  Item not found in EQUELLA")
                                        else:
                                            # find item with highest version
                                            highestVersionFound = 0
                                            highestLiveVersionFound = 0
                                            for itemResult in results.iterate("result"):
                                                if (
                                                    int(
                                                        itemResult.getNode(
                                                            "xml/item/@version"
                                                        )
                                                    )
                                                    > highestVersionFound
                                                ):

                                                    itemXml = itemResult.getSubtree(
                                                        "xml"
                                                    )
                                                    itemID = itemResult.getNode(
                                                        "xml/item/@id"
                                                    )

                                                    highestVersionFound = int(
                                                        itemResult.getNode(
                                                            "xml/item/@version"
                                                        )
                                                    )
                                                    if (
                                                        itemResult.getNode(
                                                            "xml/item/@status"
                                                        )
                                                        == "live"
                                                    ):
                                                        highestLiveVersionFound = (
                                                            highestVersionFound
                                                        )

                                            if itemVersion == 0:
                                                itemVersion = highestLiveVersionFound
                                            else:
                                                itemVersion = highestVersionFound
                                            itemFound = True
                                    if itemFound:
                                        self.echo(
                                            "  Item exists in EQUELLA ("
                                            + itemID
                                            + "/"
                                            + str(itemVersion)
                                            + ")"
                                        )
                                else:
                                    self.echo("  Item not found in EQUELLA")
                            else:
                                self.echo("  No source identifier specified")

                        # if Target Identifier column specified edit item by ID (using latest version of item)
                        elif targetIdentifierColumn != -1:
                            if (
                                self.csvArray[rowCounter][
                                    targetIdentifierColumn
                                ].strip()
                                != ""
                            ):
                                targetIdentifier = self.csvArray[rowCounter][
                                    targetIdentifierColumn
                                ].strip()
                                self.echo("  Target identifier = " + targetIdentifier)
                                if (
                                    targetVersionColumn != -1
                                    and self.csvArray[rowCounter][
                                        targetVersionColumn
                                    ].strip()
                                    != ""
                                ):
                                    self.echo(
                                        "  Target version = "
                                        + self.csvArray[rowCounter][
                                            targetVersionColumn
                                        ].strip()
                                    )
                                elif self.includeNonLive:
                                    itemVersion = -1

                                itemID = targetIdentifier

                                # try retreiving item
                                try:
                                    itemXml = tle.getItem(itemID, itemVersion)
                                    itemFound = True
                                    self.echo(
                                        "  Item exists in EQUELLA ("
                                        + itemID
                                        + "/"
                                        + itemXml.getNode("item/@version")
                                        + ")"
                                    )
                                except:
                                    self.echo(
                                        "  Could not find item ("
                                        + str(sys.exc_info()[1])
                                        + ")"
                                    )
                            else:
                                self.echo("  No target identifier specified")

                        if itemFound:
                            rowData = self.exportItem(
                                rowCounter,
                                itemXml,
                                tle,
                                itemdefuuid,
                                testOnly,
                                sourceIdentifierColumn,
                                targetIdentifierColumn,
                                targetVersionColumn,
                                commandOptionsColumn,
                                attachmentLocationsColumn,
                                collectionIDs,
                                self.csvArray[rowCounter],
                            )

                            if not self.Skip:
                                self.csvArray[rowCounter] = rowData
                                self.successCount += 1

                    except:
                        exactError = str(sys.exc_info()[1])
                        self.errorCount += 1

                        # form error string for debugging
                        errorDebug = ""
                        if self.debug:
                            exceptionType, exceptionValue, exceptionTraceback = (
                                sys.exc_info()
                            )
                            errorDebug = "\n" + "".join(
                                str(line)
                                for line in traceback.format_exception(
                                    exceptionType, exceptionValue, exceptionTraceback
                                )
                            )

                        exactError = self.translateError(str(exactError))
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + "ERROR: %s%s" % (str(exactError), str(errorDebug)),
                            style=2,
                        )

                        # halt processing if the error will apply to all rows
                        if allRowsError:
                            raise Exception("Halting process")
                # stop processing
                else:
                    if self.StopProcessing:
                        self.echo("---")
                        self.echo(
                            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                            + "Export halted by user"
                        )
                    break

        self.echo("---")

        # run End Script
        if self.endScript.strip() != "":
            try:
                exec(
                    self.endScript,
                    {
                        "IMPORT": 0,
                        "EXPORT": 1,
                        "mode": 1,
                        "vars": self.scriptVariables,
                        "testOnly": testOnly,
                        "institutionUrl": tle.institutionUrl,
                        "collection": self.collection,
                        "csvFilePath": self.csvFilePath,
                        "username": self.username,
                        "logger": self.logger,
                        "columnHeadings": self.columnHeadings,
                        "columnSettings": self.currentColumns,
                        "successCount": self.successCount,
                        "errorCount": self.errorCount,
                        "process": self.process,
                        "basepath": self.absoluteAttachmentsBasepath,
                        "csvData": self.csvArray,
                        "sourceIdentifierIndex": sourceIdentifierColumn,
                        "targetIdentifierIndex": targetIdentifierColumn,
                        "targetVersionIndex": targetVersionColumn,
                        "ebi": self.ebiScriptObject,
                        "equella": tle,
                    },
                )
            except:
                if self.debug:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    scriptErrorMsg = "An error occured in the End Script:\n" + "".join(
                        str(line)
                        for line in traceback.format_exception(
                            exceptionType, exceptionValue, exceptionTraceback
                        )
                    )
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + scriptErrorMsg
                    )
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(
                        str(line)
                        for line in traceback.format_exception_only(
                            exceptionType, exceptionValue
                        )
                    )[:-1]
                    scriptErrorMsg = (
                        "An error occured in the End Script:\n%s (line %s)"
                        % (
                            formattedException,
                            traceback.extract_tb(exceptionTraceback)[-1][1],
                        )
                    )
                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + scriptErrorMsg
                    )

        # open csv writer and output write local copy to csv
        self.echo(
            time.strftime("%H:%M:%S: ", time.localtime(time.time()))
            + "DEBUG: testOnly=%s, csvFilePath=%s, is_dir=%s"
            % (testOnly, self.csvFilePath, os.path.isdir(self.csvFilePath))
        )
        # Write back to original CSV if Row Error column exists (even in test mode) or if not test mode
        if (not testOnly or rowErrorColumn != -1) and not os.path.isdir(
            self.csvFilePath
        ):
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "Writing %d rows to CSV file: %s"
                % (len(self.csvArray), self.csvFilePath)
            )
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "DEBUG: Header row: %s" % str(self.csvArray[0])
            )
            if len(self.csvArray) > 1:
                self.echo(
                    time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                    + "DEBUG: First data row: %s" % str(self.csvArray[1])
                )
            with open(self.csvFilePath, "w", encoding=self.encoding, newline="") as f:
                writer = csv.writer(f)
                writer.writerows(self.csvArray)
                f.flush()
                os.fsync(f.fileno())
            self.echo(
                time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                + "CSV file written successfully (file size: %d bytes)"
                % os.path.getsize(self.csvFilePath)
            )

    def exportItem(
        self,
        rowCounter,
        itemXml,
        tle,
        itemdefuuid,
        testOnly,
        sourceIdentifierColumn,
        targetIdentifierColumn,
        targetVersionColumn,
        commandOptionsColumn,
        attachmentLocationsColumn,
        collectionIDs,
        oldRowData=None,
    ):

        itemID = itemXml.getNode("item/@id")
        itemVersion = itemXml.getNode("item/@version")

        self.tryPausing("[Paused]")

        # run Row Pre-Script
        if self.preScript.strip() != "":

            ebiScriptObject = EbiScriptObject(self)

            try:
                exec(
                    self.preScript,
                    {
                        "IMPORT": 0,
                        "EXPORT": 1,
                        "action": 1,
                        "vars": self.scriptVariables,
                        "rowCounter": rowCounter,
                        "testOnly": testOnly,
                        "institutionUrl": tle.institutionUrl,
                        "collection": self.collection,
                        "csvFilePath": self.csvFilePath,
                        "username": self.username,
                        "logger": self.logger,
                        "columnHeadings": self.columnHeadings,
                        "columnSettings": self.currentColumns,
                        "successCount": self.successCount,
                        "errorCount": self.errorCount,
                        "itemId": itemID,
                        "itemVersion": itemVersion,
                        "xml": itemXml,
                        "xmldom": itemXml.root,
                        "process": self.process,
                        "basepath": self.absoluteAttachmentsBasepath,
                        "sourceIdentifierIndex": sourceIdentifierColumn,
                        "targetIdentifierIndex": targetIdentifierColumn,
                        "targetVersionIndex": targetVersionColumn,
                        "csvData": self.csvArray,
                        "ebi": self.ebiScriptObject,
                        "equella": tle,
                    },
                )

            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(
                        str(line)
                        for line in traceback.format_exception_only(
                            exceptionType, exceptionValue
                        )
                    )[:-1]
                    scriptErrorMsg = (
                        "An error occured in the Row Pre-Script:\n%s (line %s)"
                        % (
                            formattedException,
                            traceback.extract_tb(exceptionTraceback)[-1][1],
                        )
                    )
                    raise Exception(scriptErrorMsg)
            self.csvFilePath = ebiScriptObject.csvFilePath

        rowData = [""] * (len(self.columnHeadings))
        filesDownloaded = []
        command = ""
        hyperlinkColumnCount = 0
        attachmentColumnCount = 0
        equellaResourceColumnCount = 0

        self.echo(
            "DEBUG: exportItem called for itemID=%s, itemVersion=%s"
            % (itemID, itemVersion)
        )
        self.echo("DEBUG: columnHeadings=%s" % str(self.columnHeadings))
        self.echo("DEBUG: Number of columns to process: %d" % len(self.columnHeadings))

        # Debug: print the XML structure to understand what paths are available
        self.echo("DEBUG: XML root node name: %s" % itemXml.root.nodeName)
        self.echo(
            "DEBUG: Testing xpath 'item/@id': %s" % str(itemXml.getNode("item/@id"))
        )
        self.echo(
            "DEBUG: Testing xpath 'item/@version': %s"
            % str(itemXml.getNode("item/@version"))
        )
        self.echo(
            "DEBUG: Testing xpath 'item/name': %s" % str(itemXml.getNode("item/name"))
        )

        if self.Skip:
            self.echo("  Skipping item")
            return rowData

        for n in range(0, len(self.columnHeadings)):
            cellValues = []
            delimiter = self.currentColumns[n][self.COLUMN_DELIMITER].strip()

            self.echo(
                "DEBUG: Processing column %d: '%s', datatype=%s"
                % (
                    n,
                    self.columnHeadings[n],
                    self.currentColumns[n][self.COLUMN_DATATYPE],
                )
            )

            # get metadata values if column datatype uses an xpath
            values = []
            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA or (
                self.currentColumns[n][self.COLUMN_DATATYPE]
                in [
                    self.ATTACHMENTLOCATIONS,
                    self.URLS,
                    self.EQUELLARESOURCES,
                    self.CUSTOMATTACHMENTS,
                ]
                and self.columnHeadings[n].strip() != ""
                and self.columnHeadings[n].strip()[0] != "#"
            ):

                # Get all matching values
                # Strip leading /xml/ if present since EQUELLA XML starts with 'item' node
                xpath = self.columnHeadings[n]
                if xpath.startswith("/xml/"):
                    xpath = xpath[5:]  # Remove '/xml/' prefix
                self.echo(
                    "DEBUG: Using xpath: '%s' (original: '%s')"
                    % (xpath, self.columnHeadings[n])
                )
                values = itemXml.getNodes(xpath)

                # detemine how many values to "discount" away (-1 means discount all of them) to
                # spread repeating values across columns with same xpaths
                valuesUsed = 0
                for i in range(0, n):
                    if (
                        self.columnHeadings[i] == self.columnHeadings[n]
                        and self.currentColumns[i][self.COLUMN_DATATYPE]
                        == self.currentColumns[n][self.COLUMN_DATATYPE]
                    ):
                        if (
                            self.currentColumns[i][self.COLUMN_DELIMITER].strip() == ""
                            and valuesUsed != -1
                        ):
                            valuesUsed += 1
                        else:
                            valuesUsed = -1

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA:
                # check if column is flagged for XML fragments
                if self.currentColumns[n][self.COLUMN_XMLFRAGMENT] == "YES":

                    # process node as XML fragment
                    xmlFragNodes = itemXml.getNodes(self.columnHeadings[n], False)
                    if len(xmlFragNodes) > 0:
                        xmlFragment = ""
                        for childNode in xmlFragNodes[0].childNodes:
                            # only add node if it is not an empty text node
                            if (
                                childNode.nodeType == Node.TEXT_NODE
                                and childNode.nodeValue.strip() != ""
                            ) or (childNode.nodeType != Node.TEXT_NODE):
                                xmlFragment += childNode.toxml()

                        cellValues.append(xmlFragment)

                # not an xml fragment
                else:
                    if len(values) > 0 and valuesUsed != -1:
                        if delimiter != "":
                            # get all non-discounted values
                            cellValues = values[valuesUsed:]
                        else:
                            if len(values) > valuesUsed:
                                cellValues.append(values[valuesUsed])

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.URLS:
                hyperlinkColumnCount += 1

                if len(values) > 0 and valuesUsed != -1:

                    attachmentNames = []

                    # calculate first and last index of values applicable to this column
                    if delimiter != "":
                        lastValueIndex = len(values)
                    else:
                        lastValueIndex = valuesUsed + 1

                    # iterate through the attachment UUIDs applicable to this column to calculate
                    # cell values whilst downloading files as necessary
                    for attachmentUUID in values[valuesUsed:lastValueIndex]:
                        for attachment in itemXml.getSubtree(
                            "item/attachments"
                        ).iterate("attachment"):
                            filename = attachment.getNode("file").replace(" ", "%20")
                            if attachment.getNode("uuid") == attachmentUUID:
                                if attachment.getNode("@type") == "remote":

                                    # get URL from attachment metadata
                                    self.echo("  Hyperlink: " + filename)

                                    # collect attachment name
                                    attachmentName = attachment.getNode("description")
                                    if attachmentName == filename:
                                        attachmentName = ""
                                    attachmentNames.append(attachmentName)

                                    # set cell value
                                    cellValues.append(filename)
                                elif attachment.getNode("@type") == "local":
                                    if self.debug:
                                        self.echo("  Ignoring: " + filename)

                    # find corresponding Attachment Names column to populate with attachment names
                    attachmentNameColumnCount = 0
                    for col in range(0, len(self.currentColumns)):
                        if (
                            self.currentColumns[col][self.COLUMN_DATATYPE]
                            == self.HYPERLINKNAMES
                        ):

                            attachmentNameColumnCount += 1

                            if attachmentNameColumnCount == hyperlinkColumnCount:
                                # populate with attachment names
                                attachmentNameColumnDelimiter = self.currentColumns[
                                    col
                                ][self.COLUMN_DELIMITER].strip()
                                if attachmentNameColumnDelimiter != "":
                                    rowData[col] = attachmentNameColumnDelimiter.join(
                                        attachmentNames
                                    )
                                else:
                                    rowData[col] = attachmentNames[0]
                                break

            elif (
                self.currentColumns[n][self.COLUMN_DATATYPE] == self.ATTACHMENTLOCATIONS
            ):
                attachmentColumnCount += 1

                if len(values) > 0 and valuesUsed != -1:

                    # get absolute path to file relative to base path (from Options) and then relative to csv folder
                    filesfolder = self.absoluteAttachmentsBasepath
                    attachmentNames = []
                    attachmentNamesZip = []
                    zipFiles = []

                    # get item URL (used for downloading files)
                    itemUrl = (
                        self.institutionUrl
                        + "/file/"
                        + itemID
                        + "/"
                        + itemVersion
                        + "/"
                    )

                    # calculate first and last index of values applicable to this column
                    if delimiter != "":
                        lastValueIndex = len(values)
                    else:
                        lastValueIndex = valuesUsed + 1

                    # iterate through the attachment UUIDs applicable to this column to calculate
                    # cell values whilst downloading files as necessary
                    for attachmentUUID in values[valuesUsed:lastValueIndex]:
                        for attachment in itemXml.getSubtree(
                            "item/attachments"
                        ).iterate("attachment"):
                            if attachment.getNode("uuid") == attachmentUUID:
                                filename = attachment.getNode("file")
                                if attachment.getNode("@type") == "local":
                                    if filename.find("/") == -1:
                                        # download simple file
                                        filepath = os.path.normpath(os.path.join(filesfolder, filename))
                                        fileUrl = itemUrl + urllib.parse.quote(filename)

                                        if (
                                            not testOnly
                                            and not fileUrl in filesDownloaded
                                        ):
                                            self.echo("  Attachment: " + filename)

                                            # "deconflict" files of same name
                                            filepath = self.deconflict(
                                                filepath,
                                                self.exportedFiles,
                                                self.overwriteMode,
                                            )

                                            tle.getFile(fileUrl, filepath)
                                            filesDownloaded.append(fileUrl)
                                            self.exportedFiles.append(filepath)

                                        # collect attachment name
                                        attachmentName = attachment.getNode(
                                            "description"
                                        )
                                        if attachmentName == filename:
                                            attachmentName = ""
                                        attachmentNames.append(attachmentName)

                                        # set cell value
                                        if not filename in cellValues:
                                            cellValues.append(
                                                os.path.relpath(filepath, filesfolder).replace("\\", "/")
                                            )
                                    else:
                                        # possibly a zip file
                                        rootFolder = filename[: filename.find("/")]
                                        if rootFolder.endswith(".zip"):
                                            # download zip file
                                            zipfilename = rootFolder
                                            relfilename = filename[
                                                filename.find("/") + 1 :
                                            ]
                                            filepath = os.path.normpath(os.path.join(
                                                filesfolder, zipfilename
                                            ))
                                            fileUrl = (
                                                itemUrl
                                                + "_zips/"
                                                + urllib.parse.quote(zipfilename)
                                            )

                                            if (
                                                not testOnly
                                                and not fileUrl in filesDownloaded
                                            ):
                                                self.echo(
                                                    "  Attachment (ZIP): " + zipfilename
                                                )

                                                # "deconflict" files of same name
                                                filepath = self.deconflict(
                                                    filepath,
                                                    self.exportedFiles,
                                                    self.overwriteMode,
                                                )

                                                tle.getFile(fileUrl, filepath)
                                                filesDownloaded.append(fileUrl)
                                                self.exportedFiles.append(filepath)

                                            # collect attachment name
                                            attachmentNamesZip.append(
                                                [
                                                    relfilename,
                                                    attachment.getNode("description"),
                                                ]
                                            )

                                            # set command
                                            if command == "":
                                                command = "UNZIP"
                                            elif command != "UNZIP":
                                                command = "AUTO"

                                            # add to cell values if zip not already there
                                            if zipfilename not in zipFiles:
                                                cellValues.append(
                                                    os.path.relpath(
                                                        filepath, filesfolder
                                                    ).replace("\\", "/")
                                                )
                                                zipFiles.append(zipfilename)

                                elif (
                                    attachment.getNode("@type") == "custom"
                                    and attachment.getNode("type") == "scorm"
                                ):
                                    # download SCORM package
                                    filepath = os.path.normpath(os.path.join(filesfolder, filename))

                                    # "deconflict" files of same name
                                    filepath = self.deconflict(
                                        filepath, self.exportedFiles, self.overwriteMode
                                    )

                                    fileUrl = (
                                        itemUrl
                                        + "_SCORM/"
                                        + urllib.parse.quote(filename)
                                    )

                                    if not testOnly and not fileUrl in filesDownloaded:
                                        self.echo("  Attachment (SCORM): " + filename)
                                        tle.getFile(fileUrl, filepath)
                                        filesDownloaded.append(fileUrl)
                                        self.exportedFiles.append(filepath)

                                    # collect attachment name
                                    attachmentName = attachment.getNode("description")
                                    if attachmentName == filename:
                                        attachmentName = ""
                                    attachmentNames = []
                                    attachmentNames.append(attachmentName)

                                    # set command
                                    if command == "":
                                        command = "IMS"
                                    elif command != "IMS":
                                        command = "AUTO"

                                    # set cell value
                                    if not filename in cellValues:
                                        cellValues.append(filename)
                                elif attachment.getNode("@type") == "remote":
                                    if self.debug:
                                        self.echo("  Ignoring: " + filename)
                                else:
                                    # attachment not supported for export
                                    self.echo(
                                        "  Unknown or unsupported attachment: "
                                        + filename
                                    )

                        if (
                            itemXml.getNode("item/itembody/packagefile/@uuid")
                            == attachmentUUID
                        ):
                            filename = itemXml.getNode("item/itembody/packagefile")

                            # download IMS package
                            filepath = os.path.normpath(os.path.join(filesfolder, filename))

                            # "deconflict" files of same name
                            filepath = self.deconflict(
                                filepath, self.exportedFiles, self.overwriteMode
                            )

                            fileUrl = itemUrl + "_IMS/" + urllib.parse.quote(filename)

                            if not testOnly and not fileUrl in filesDownloaded:
                                self.echo("  Attachment (IMS): " + filename)
                                tle.getFile(fileUrl, filepath)
                                filesDownloaded.append(fileUrl)
                                self.exportedFiles.append(filepath)

                            # collect attachment name
                            attachmentName = itemXml.getNode(
                                "item/itembody/packagefile/@name"
                            )
                            if attachmentName == filename:
                                attachmentName = ""
                            attachmentNames = []
                            attachmentNames.append(attachmentName)

                            # set command
                            if command == "":
                                command = "IMS"
                            elif command != "IMS":
                                command = "AUTO"

                            # set cell value
                            if not filename in cellValues:
                                cellValues.append(filename)

                    # find corresponding Attachment Names column to populate with attachment names
                    attachmentNameColumnCount = 0
                    for col in range(0, len(self.currentColumns)):
                        if (
                            self.currentColumns[col][self.COLUMN_DATATYPE]
                            == self.ATTACHMENTNAMES
                        ):

                            attachmentNameColumnCount += 1

                            if attachmentNameColumnCount == attachmentColumnCount:
                                # populate with attachment names
                                if len(attachmentNamesZip) == 0:
                                    attachmentNameColumnDelimiter = self.currentColumns[
                                        col
                                    ][self.COLUMN_DELIMITER].strip()
                                    if attachmentNameColumnDelimiter != "":
                                        rowData[col] = (
                                            attachmentNameColumnDelimiter.join(
                                                attachmentNames
                                            )
                                        )
                                    else:
                                        rowData[col] = attachmentNames[0]
                                else:
                                    attachmentName = "("
                                    for pair in attachmentNamesZip:
                                        attachmentName += "("
                                        attachmentName += (
                                            '"' + pair[0] + '","' + pair[1] + '"'
                                        )
                                        attachmentName += "),"
                                    attachmentName = attachmentName[:-1]
                                    attachmentName += ")"
                                    rowData[col] = attachmentName
                                break

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.OWNER:

                self.echo("  Exporting owner")

                # get owner ID
                userID = itemXml.getNodes("item/owner")[0]

                try:
                    # get username from user ID
                    username = tle.getUser(userID).getNode("username")
                except:

                    # handle inability to retrieve username from user ID
                    if self.saveNonexistentUsernamesAsIDs:
                        self.echo(
                            "  User ID '%s' not found so exporting raw." % (userID)
                        )
                        username = userID
                    else:
                        raise Exception(
                            "No user found with matching user ID: %s" % userID
                        )
                cellValues = [username]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMID:
                cellValues = [itemID]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMVERSION:
                cellValues = [itemVersion]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.COLLABORATORS:

                self.echo("  Exporting collaborators")

                # get collaborators
                userIDs = itemXml.getNodes("item/collaborativeowners/collaborator")

                if delimiter == "" and len(userIDs) > 1:
                    userIDs = userIDs[:1]

                cellValues = []

                for userID in userIDs:
                    try:
                        # get username from user ID
                        username = tle.getUser(userID).getNode("username")
                    except:

                        # handle inability to retrieve username from user ID
                        if self.saveNonexistentUsernamesAsIDs:
                            self.echo(
                                "  User ID '%s' not found so exporting raw." % (userID)
                            )
                            username = userID
                        else:
                            raise Exception(
                                "No user found with matching user ID: %s" % userID
                            )
                    cellValues.append(username)

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.COLLECTION:
                collID = itemXml.getNode("item/@itemdefid")
                collName = next(
                    (key for key, value in collectionIDs.items() if value == collID)
                )
                cellValues = [collName]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMID:
                cellValues = [itemID]

            elif self.currentColumns[n][self.COLUMN_DATATYPE] == self.ITEMVERSION:
                cellValues = [itemVersion]

            elif (
                self.currentColumns[n][self.COLUMN_DATATYPE] == self.ATTACHMENTLOCATIONS
            ):
                attachmentColumnCount += 1

            elif self.currentColumns[n][self.COLUMN_DATATYPE] in [
                self.IGNORE,
                self.TARGETIDENTIFIER,
                self.TARGETVERSION,
            ]:
                if oldRowData != None:
                    cellValues = [oldRowData[n]]

            # delimit cell values
            cellValue = delimiter.join(cellValues)

            self.echo(
                "DEBUG: Column %d cellValues=%s, cellValue='%s'"
                % (n, str(cellValues), cellValue)
            )

            # display to log if necessary
            if self.currentColumns[n][self.COLUMN_DISPLAY] == "YES":
                self.echo("  %s: %s" % (self.columnHeadings[n], cellValue))

            # populate delimited list of cell values in row data
            if len(cellValues) > 0:
                rowData[n] = cellValue
                self.echo("DEBUG: Set rowData[%d] = '%s'" % (n, cellValue))
            else:
                self.echo(
                    "DEBUG: Column %d has no cellValues, rowData[%d] remains empty"
                    % (n, n)
                )

        # add Commands cell
        if commandOptionsColumn != -1:
            rowData[commandOptionsColumn] = command

        # run Row Post-Script
        if self.postScript.strip() != "":
            try:
                exec(
                    self.postScript,
                    {
                        "IMPORT": 0,
                        "EXPORT": 1,
                        "action": 1,
                        "vars": self.scriptVariables,
                        "rowData": rowData,
                        "rowCounter": rowCounter,
                        "testOnly": testOnly,
                        "institutionUrl": tle.institutionUrl,
                        "collection": self.collection,
                        "csvFilePath": self.csvFilePath,
                        "username": self.username,
                        "logger": self.logger,
                        "columnHeadings": self.columnHeadings,
                        "columnSettings": self.currentColumns,
                        "successCount": self.successCount,
                        "errorCount": self.errorCount,
                        "itemId": itemID,
                        "itemVersion": itemVersion,
                        "xml": itemXml,
                        "xmldom": itemXml.root,
                        "process": self.process,
                        "basepath": self.absoluteAttachmentsBasepath,
                        "sourceIdentifierIndex": sourceIdentifierColumn,
                        "targetIdentifierIndex": targetIdentifierColumn,
                        "targetVersionIndex": targetVersionColumn,
                        "csvData": self.csvArray,
                        "ebi": self.ebiScriptObject,
                        "equella": tle,
                    },
                )
            except:
                if self.debug:
                    raise
                else:
                    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                    formattedException = "".join(
                        str(line)
                        for line in traceback.format_exception_only(
                            exceptionType, exceptionValue
                        )
                    )[:-1]
                    scriptErrorMsg = (
                        "An error occured in the Row Post-Script:\n%s (line %s)"
                        % (
                            formattedException,
                            traceback.extract_tb(exceptionTraceback)[-1][1],
                        )
                    )
                    raise Exception(scriptErrorMsg)
        if testOnly:
            self.echo("  Item valid for export")
        else:
            self.echo("  Item successfully exported")
        return rowData

    def deconflict(self, filepath, exportedFiles, overwriteMode):
        deconflictedFilepath = filepath

        if overwriteMode == self.OVERWRITEEXISTING:
            if filepath in exportedFiles:
                conflictFolderNumber = 0
                conflictFolderUsed = True
                while conflictFolderUsed:
                    conflictFolderNumber += 1
                    conflictFilepath = os.path.join(
                        os.path.dirname(filepath),
                        str(conflictFolderNumber),
                        os.path.basename(filepath),
                    )
                    if conflictFilepath not in exportedFiles:
                        conflictFolderUsed = False
                        if not os.path.exists(os.path.dirname(conflictFilepath)):
                            os.makedirs(os.path.dirname(conflictFilepath))
                        deconflictedFilepath = conflictFilepath

        elif overwriteMode == self.OVERWRITENONE:
            if os.path.isfile(filepath):
                conflictFolderNumber = 0
                conflictFolderUsed = True
                while conflictFolderUsed:
                    conflictFolderNumber += 1
                    conflictFilepath = os.path.join(
                        os.path.dirname(filepath),
                        str(conflictFolderNumber),
                        os.path.basename(filepath),
                    )
                    if not os.path.isfile(conflictFilepath):
                        conflictFolderUsed = False
                        if not os.path.exists(os.path.dirname(conflictFilepath)):
                            os.makedirs(os.path.dirname(conflictFilepath))
                        deconflictedFilepath = conflictFilepath

        return deconflictedFilepath


# script object used by EBI scripts
class EbiScriptObject(object):
    def __init__(self, parent):
        self.parent = parent

    def getCsvFilePath(self):
        return self.parent.csvFilePath

    def setCsvFilePath(self, value):
        self.parent.csvFilePath = value

    csvFilePath = property(getCsvFilePath, setCsvFilePath)

    def getBasepath(self):
        return self.parent.absoluteAttachmentsBasepath

    def setBasepath(self, value):
        self.parent.absoluteAttachmentsBasepath = value

    basepath = property(getBasepath, setBasepath)

    def loadCsv(self):
        self.parent.loadCSV(self.parent.owner)


# Logger class only used by EBI scripts
class Logger:
    def __init__(self, parent):
        self.parent = parent

    def log(self, entry, display=True, log=True):
        if not isinstance(entry, str):
            entry = str(entry)
        self.parent.echo(entry=entry, display=display, log=log, style=3)


# Process class only used by EBI scripts
class Process:
    def __init__(self, parent):
        self.parent = parent
        self.halted = False

    def halt(self):
        self.parent.StopProcessing = True
        self.parent.processingStoppedByScript = True
        self.halted = True

    def skip(self):
        self.parent.Skip = True
