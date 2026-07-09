import sys
import os
import traceback
import time
import zipfile
import wx
import urllib.parse
from equellaclient import *
import Constants
import Utils
import uuid

from dataclasses import dataclass


@dataclass
class RowContext:
    """
    Data Transfer Object holding all parameter states needed to process a single CSV row.
    This encapsulates the many columns passed between the UI, the Engine, and the RowProcessor,
    making signatures clean and preserving state without mutating self during iterations.
    """

    rowCounter: int
    meta: list
    tle: object
    itemdefuuid: str
    collectionIDs: dict
    testOnly: bool
    sourceIdentifierColumn: int
    targetIdentifierColumn: int
    targetVersionColumn: int
    commandOptionsColumn: int
    attachmentLocationsColumn: int
    urlsColumn: int
    resourcesColumn: int
    customAttachmentsColumn: int
    collectionColumn: int
    thumbnailsColumn: int
    selectedThumbnailColumn: int
    ownerColumn: int
    collaboratorsColumn: int
    rowErrorColumn: int


class RowProcessor:
    """
    Core engine delegate designed to handle the complex business logic of pulling data from
    a parsed CSV row and orchestrating EQUELLA API updates/imports on an Item level.

    Acts as a proxy connecting tightly to the Engine instance while encapsulating the row logic
    for readability, error safety, and testability.
    """

    def __init__(self, engine):
        # We store the parent engine instance natively avoiding __setattr__ infinite recursion
        object.__setattr__(self, "engine", engine)

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def __setattr__(self, name, value):
        if hasattr(self.engine, name):
            setattr(self.engine, name, value)
        else:
            object.__setattr__(self, name, value)

    def _resolve_user_id(self, tle, username, fallback_to_id=False):
        """Helper to find user by username. Returns (userUUID, is_all_rows_error_potentially)"""
        try:
            matchingUsers = tle.searchUsersByGroup("", username)
        except Exception as e:
            error = str(e)
            if error.rfind("HTTP") != -1 and error.rfind("404") != -1:
                return None, True  # allRowsError = True
            raise Exception(error)

        matchingUserNodes = matchingUsers.getNodes("user", False)

        # if any matches, try to find exact username match
        if len(matchingUserNodes) > 0:
            for userNode in matchingUserNodes:
                try:
                    userUUID = userNode.getElementsByTagName("uuid")[
                        0
                    ].firstChild.nodeValue
                    userInfo = tle.getUser(userUUID)
                    retrieved_username = userInfo.getNode("username")
                    if (
                        retrieved_username
                        and retrieved_username.strip().lower() == username.lower()
                    ):
                        return userUUID, False
                except Exception as e:
                    # If getUser fails, skip this user
                    pass

            # If no exact match found, use first result
            return (
                matchingUserNodes[0]
                .getElementsByTagName("uuid")[0]
                .firstChild.nodeValue,
                False,
            )

        if fallback_to_id:
            return username, False

        return None, False

    def _find_existing_item(self, ctx, itemVersion):
        tle, itemdefuuid, meta, sourceIdentifierColumn, columnHeadings = (
            ctx.tle,
            ctx.itemdefuuid,
            ctx.meta,
            ctx.sourceIdentifierColumn,
            self.columnHeadings,
        )
        sourceIdentifier = meta[sourceIdentifierColumn].strip()
        self.echo("  Source identifier = " + sourceIdentifier)
        if sourceIdentifier.find("'") != -1:
            raise Exception("Source identifier cannot contain apostrophes")

        searchFilter = (
            "/xml/"
            + columnHeadings[sourceIdentifierColumn]
            + "='"
            + sourceIdentifier
            + "'"
        )

        onlyLive = itemVersion == 0
        limit = 50 if itemVersion != 0 else 1

        results = tle.search(
            0,
            limit,
            "/item/name",
            [itemdefuuid],
            searchFilter,
            query="",
            onlyLive=onlyLive,
        )

        if int(results.getNode("available")) > 0:
            if itemVersion == 0:
                itemID = results.getNode("result/xml/item/@id")
                itemVersion = results.getNode("result/xml/item/@version")
            elif itemVersion != -1:
                itemFound = False
                for itemResult in results.iterate("result"):
                    if itemResult.getNode("xml/item/@version") == str(itemVersion):
                        itemID = itemResult.getNode("xml/item/@id")
                        itemFound = True
                        break
                if not itemFound:
                    raise Exception("Item not found")
            else:
                highestVersionFound = 0
                for itemResult in results.iterate("result"):
                    if (
                        int(itemResult.getNode("xml/item/@version"))
                        > highestVersionFound
                    ):
                        highestVersionFound = int(
                            itemResult.getNode("xml/item/@version")
                        )
                        itemID = itemResult.getNode("xml/item/@id")
                        itemVersion = highestVersionFound

            self.echo(
                "  Item exists in EQUELLA (" + itemID + "/" + str(itemVersion) + ")"
            )
            return itemID, itemVersion, False
        else:
            if itemVersion == 0 or itemVersion == -1:
                self.echo("  Item not found")
                return "nil", itemVersion, True
            else:
                raise Exception("Item not found")

    def _find_matching_name_for_column(
        self, ctx, current_column_count, target_datatype, actualDelimiter, value_index
    ):
        meta = ctx.meta
        name_column_count = 0
        for col in range(0, len(meta)):
            if self.currentColumns[col][self.COLUMN_DATATYPE] == target_datatype:
                name_column_count += 1
                if name_column_count == current_column_count:
                    names = meta[col].split(actualDelimiter)
                    if value_index < len(names) and names[value_index].strip() != "":
                        return names[value_index]
                    break
        return ""

    def _process_custom_attachments(
        self, item, custom_attachments_xml, columnHeading, thumbnailSelected
    ):
        xmlAttachmentElementsFragmentString = (
            '<?xml version="1.0" encoding="%s"?><fragment>%s</fragment>'
            % (self.encoding, custom_attachments_xml)
        )
        xmlAttachmentElements = PropBagEx(
            xmlAttachmentElementsFragmentString, encoding=self.encoding
        )

        for attachmentElement in xmlAttachmentElements.iterate("attachment"):
            attachmentUUID = attachmentElement.getNode("uuid")
            if attachmentUUID == None or attachmentUUID == "":
                attachmentUUID = str(uuid.uuid4())
                attachmentElement.setNode("uuid", attachmentUUID)
                if attachmentElement.getNode("selected_thumbnail") == "true":
                    item.getXml().setNode("item/thumbnail", "custom:" + attachmentUUID)
                    thumbnailSelected = True

            item.getXml().setNode("item/attachments", "")
            item.getXml().root.getElementsByTagName("item")[0].getElementsByTagName(
                "attachments"
            )[0].appendChild(attachmentElement.root.cloneNode(True))

            if self.attachmentMetadataTargets:
                if columnHeading.strip() != "" and columnHeading[:1] != "#":
                    item.getXml().createNode(columnHeading, attachmentUUID)

        return thumbnailSelected

    def _process_metadata_column(
        self, item, n, meta_value, commandOptions, actualDelimiter
    ):
        columnHeading = self.columnHeadings[n]
        isXmlFragment = self.currentColumns[n][self.COLUMN_XMLFRAGMENT] == "YES"
        isDisplay = self.currentColumns[n][self.COLUMN_DISPLAY] == "YES"
        is_first_occurrence = self.columnHeadings[:n].count(columnHeading) == 0

        if isXmlFragment:
            if isDisplay:
                self.echo("  %s: %s" % (columnHeading, meta_value.strip()))
            if meta_value.strip() != "":
                xmlFragmentString = (
                    '<?xml version="1.0" encoding="UTF-8"?><fragment>%s</fragment>'
                    % (meta_value)
                )
                xmlFragment = PropBagEx(str(xmlFragmentString))
                stripNode(xmlFragment.root, True)
                if len(item.prop.getNodes(columnHeading, False)) == 0:
                    item.getXml().createNode(columnHeading, "")
                else:
                    if (
                        is_first_occurrence
                        and self.existingMetadataMode != self.APPENDMETA
                        and "APPENDMETA" not in commandOptions
                    ):
                        for child in xmlFragment.root.childNodes:
                            item.prop.removeNode(columnHeading + "/" + child.nodeName)
                parentNodes = item.prop.getNodes(columnHeading, False)
                if len(parentNodes) > 0:
                    parentNode = parentNodes[0]
                    if hasattr(parentNode, "appendChild"):
                        for child in xmlFragment.root.childNodes:
                            parentNode.appendChild(child.cloneNode(True))
            else:
                if (
                    self.existingMetadataMode != self.APPENDMETA
                    and "APPENDMETA" not in commandOptions
                ):
                    if len(item.prop.getNodes(columnHeading, False)) != 0:
                        parentNode = item.prop.getNodes(columnHeading, False)[0]
                        for child in parentNode.childNodes:
                            if child.nodeType == Node.TEXT_NODE:
                                child.nodeValue = ""
        else:
            newValues = meta_value.split(actualDelimiter)
            if (
                is_first_occurrence
                and self.existingMetadataMode != self.APPENDMETA
                and "APPENDMETA" not in commandOptions
            ):
                item.getXml().removeNode(columnHeading)
            for i in range(len(newValues)):
                if isDisplay:
                    self.echo("  %s: %s" % (columnHeading, newValues[i].strip()))
                if newValues[i].strip() != "":
                    if newValues[i].strip().lower() == "<null>":
                        newValues[i] = ""
                    item.getXml().createNode(columnHeading, str(newValues[i].strip()))

    def _process_attachment_file(
        self,
        item,
        filepath,
        filename,
        filesize,
        attachmentLinkName,
        commandOptions,
        testOnly,
        n,
        columnHeading,
        thumbnail_value,
        thumbnails,
        selectedThumbnail,
        thumbnailSelected,
    ):
        uploadStatus = "   "
        attachmentType = self.attachmentTypeFile
        if (
            "UNZIP" in commandOptions
            or "IMS" in commandOptions
            or "SCORM" in commandOptions
            or "AUTO" in commandOptions
        ):
            if os.path.splitext(filename)[1].upper() == ".ZIP":
                self.echo("    Attachment is a zip file")
                zfobj = zipfile.ZipFile(filepath)
                if (
                    "IMS" in commandOptions
                    or "SCORM" in commandOptions
                    or "AUTO" in commandOptions
                ):
                    if "imsmanifest.xml" in zfobj.namelist():
                        imsmanifest = PropBagEx(
                            zfobj.read("imsmanifest.xml").decode("utf-8")
                        )
                        self.echo("    IMS manifest found, treat as IMS package")
                        attachmentUUID = str(uuid.uuid4())
                        if self.attachmentMetadataTargets:
                            if columnHeading.strip() != "" and columnHeading[:1] != "#":
                                item.getXml().createNode(columnHeading, attachmentUUID)
                        if attachmentLinkName == "":
                            attachmentLinkName = filename

                        if "IMS" in commandOptions or "AUTO" in commandOptions:
                            if (
                                self.scormformatsupport
                                and imsmanifest.getNode("metadata/schema")
                                == "ADL SCORM"
                            ):
                                self.echo("    Package is a SCORM package")
                                item.attachSCORM(
                                    Utils.openFileForReading(filepath),
                                    filename,
                                    attachmentLinkName,
                                    uploadStatus,
                                    not testOnly,
                                    filesize,
                                    attachmentUUID,
                                    self.chunkSize,
                                )
                            else:
                                item.attachIMS(
                                    Utils.openFileForReading(filepath),
                                    filename,
                                    attachmentLinkName,
                                    uploadStatus,
                                    not testOnly,
                                    filesize,
                                    attachmentUUID,
                                    self.chunkSize,
                                )
                            attachmentType = self.attachmentTypeIMS

                        if "SCORM" in commandOptions:
                            item.attachSCORM(
                                Utils.openFileForReading(filepath),
                                filename,
                                attachmentLinkName,
                                uploadStatus,
                                not testOnly,
                                filesize,
                                attachmentUUID,
                                self.chunkSize,
                            )
                            attachmentType = self.attachmentTypeSCORM
                    elif "AUTO" in commandOptions:
                        self.echo("    No IMS manifest found, treat as simple zip file")
                        self._processUnzipAttachment(
                            item,
                            filename,
                            filepath,
                            filesize,
                            attachmentLinkName,
                            uploadStatus,
                            n,
                            zfobj,
                            testOnly,
                            columnHeading if self.attachmentMetadataTargets else None,
                        )
                        attachmentType = self.attachmentTypeZip
                    elif "IMS" in commandOptions or "SCORM" in commandOptions:
                        raise Exception(
                            "No IMS manifest found, cannot use IMS or SCORM command option"
                        )
                elif "UNZIP" in commandOptions:
                    self._processUnzipAttachment(
                        item,
                        filename,
                        filepath,
                        filesize,
                        attachmentLinkName,
                        uploadStatus,
                        n,
                        zfobj,
                        testOnly,
                        columnHeading if self.attachmentMetadataTargets else None,
                    )
                    attachmentType = self.attachmentTypeZip
            elif "AUTO" in commandOptions:
                if not testOnly:
                    item.attachFile(
                        filename,
                        Utils.openFileForReading(filepath),
                        uploadStatus,
                        self.chunkSize,
                    )
                attachmentType = self.attachmentTypeFile
            elif "UNZIP" in commandOptions:
                raise Exception(
                    "Not a zip file, cannot use UNZIP or IMS command options"
                )
            else:
                if not testOnly:
                    item.attachFile(
                        filename,
                        Utils.openFileForReading(filepath),
                        uploadStatus,
                        self.chunkSize,
                    )
                attachmentType = self.attachmentTypeFile
        else:
            if not testOnly:
                item.attachFile(
                    filename,
                    Utils.openFileForReading(filepath),
                    uploadStatus,
                    self.chunkSize,
                )
            attachmentType = self.attachmentTypeFile

        if attachmentType == self.attachmentTypeFile:
            attachmentUUID = str(uuid.uuid4())
            thumbnail = ""
            if thumbnails:
                thumbnail = "suppress" if thumbnail_value not in thumbnails else ""
                for thumb in thumbnails:
                    thumbparts = thumb.split(":")
                    if (
                        len(thumbparts) == 2
                        and thumbparts[0].strip() == thumbnail_value
                    ):
                        thumbnail = thumbparts[1].strip()
                if "*" + os.path.splitext(filepath)[1].lower() in (
                    wildcard.lower() for wildcard in thumbnails
                ):
                    thumbnail = ""

            customXPath = None
            if columnHeading.strip() != "" and not columnHeading.startswith("#"):
                customXPath = columnHeading

            if attachmentLinkName != "":
                item.addStartPage(
                    attachmentLinkName,
                    filename,
                    filesize,
                    attachmentUUID,
                    thumbnail,
                    self.appendAttachments,
                    customXPath,
                )
            else:
                item.addStartPage(
                    filename,
                    filename,
                    filesize,
                    attachmentUUID,
                    thumbnail,
                    self.appendAttachments,
                    customXPath,
                )

            if self.attachmentMetadataTargets and not customXPath:
                if columnHeading.strip() != "" and columnHeading[:1] != "#":
                    item.getXml().createNode(columnHeading, attachmentUUID)

            if thumbnail_value == selectedThumbnail:
                item.getXml().setNode("item/thumbnail", "custom:" + attachmentUUID)
                thumbnailSelected = True
            elif (
                thumbnail != "suppress"
                and not thumbnailSelected
                and "*" + os.path.splitext(filepath)[1].lower() == selectedThumbnail
            ):
                item.getXml().setNode("item/thumbnail", "custom:" + attachmentUUID)
                thumbnailSelected = True

        return thumbnailSelected

    def _process_urls(
        self, ctx, item, n, meta_value, actualDelimiter, hyperlinkColumnCount
    ):
        if self.attachmentMetadataTargets and not self.appendAttachments:
            if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0:
                item.getXml().removeNode(self.columnHeadings[n])

        values = meta_value.split(actualDelimiter)
        for i in range(len(values)):
            if values[i].strip() != "":
                url = str(values[i].replace(" ", "%20"))
                self.echo("  Hyperlink: " + url)

                hyperlinkName = self._find_matching_name_for_column(
                    ctx, hyperlinkColumnCount, self.HYPERLINKNAMES, actualDelimiter, i
                )
                attachmentUUID = str(uuid.uuid4())

                if hyperlinkName != "":
                    item.addUrl(hyperlinkName, url, attachmentUUID)
                else:
                    item.addUrl(url, url, attachmentUUID)

                if self.attachmentMetadataTargets:
                    if (
                        self.columnHeadings[n].strip() != ""
                        and self.columnHeadings[n][:1] != "#"
                    ):
                        item.getXml().createNode(self.columnHeadings[n], attachmentUUID)

    def _process_equella_resources(
        self,
        ctx,
        item,
        n,
        meta_value,
        actualDelimiter,
        equellaResourceColumnCount,
        commandOptions,
        calHoldingMetadataTarget,
    ):
        itemdefuuid, collectionIDs, sourceIdentifierColumn, meta = (
            ctx.itemdefuuid,
            ctx.collectionIDs,
            ctx.sourceIdentifierColumn,
            ctx.meta,
        )
        isCalHolding = False
        if calHoldingMetadataTarget == "" and "CAL_PORTION" in commandOptions:
            isCalHolding = True
            calHoldingMetadataTarget = self.columnHeadings[n]

        if self.attachmentMetadataTargets and not self.appendAttachments:
            if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0:
                item.getXml().removeNode(self.columnHeadings[n])

        values = meta_value.split(actualDelimiter)
        for i in range(len(values)):
            if values[i].strip() != "":
                resourceUrl = str(values[i])
                self.echo("  EQUELLA resource: " + resourceUrl)
                (
                    resourceItemUuid,
                    resourceItemVersion,
                    resourceAttachmentUuid,
                    resourceName,
                ) = self.getEquellaResourceDetail(
                    resourceUrl,
                    itemdefuuid,
                    collectionIDs,
                    sourceIdentifierColumn,
                    isCalHolding,
                )
                if self.debug:
                    self.echo("   resourceItemUuid = " + resourceItemUuid)
                    self.echo("   resourceItemVersion = " + str(resourceItemVersion))
                    self.echo("   resourceAttachmentUuid = " + resourceAttachmentUuid)
                    self.echo("   resourceName = " + resourceName)

                found_resource_name = self._find_matching_name_for_column(
                    ctx,
                    equellaResourceColumnCount,
                    self.EQUELLARESOURCENAMES,
                    actualDelimiter,
                    i,
                )
                if found_resource_name:
                    resourceName = found_resource_name

                attachmentUUID = str(uuid.uuid4())
                item.attachResource(
                    resourceItemUuid,
                    resourceItemVersion,
                    resourceName,
                    attachmentUUID,
                    resourceAttachmentUuid,
                )

                if self.attachmentMetadataTargets:
                    if (
                        self.columnHeadings[n].strip() != ""
                        and self.columnHeadings[n][:1] != "#"
                    ):
                        item.getXml().createNode(self.columnHeadings[n], attachmentUUID)
        return calHoldingMetadataTarget

    def _process_attachment_locations(
        self,
        ctx,
        item,
        n,
        meta_value,
        actualDelimiter,
        attachmentColumnCount,
        commandOptions,
        thumbnails,
        selectedThumbnail,
        thumbnailSelected,
    ):
        testOnly, meta = ctx.testOnly, ctx.meta
        # delete all attachment metadata targets if this is the first occurence (but not in append attachments mode)
        if self.attachmentMetadataTargets and not self.appendAttachments:
            if self.columnHeadings[:n].count(self.columnHeadings[n]) == 0:
                item.getXml().removeNode(self.columnHeadings[n])

        # split for multi-value field
        values = meta_value.split(actualDelimiter)
        for i in range(len(values)):
            if values[i].strip() != "":

                # get absolute path to file
                filepath = os.path.normpath(os.path.join(self.absoluteAttachmentsBasepath, values[i]))

                # Validate file path exists
                if not os.path.exists(filepath):
                    raise Exception("File not found: '%s'" % filepath)

                # ensure that attachment specified is not a directory
                if os.path.isdir(filepath):
                    raise Exception("'%s' is a directory, not a file" % filepath)

                # Validate file can be read
                if not os.access(filepath, os.R_OK):
                    raise Exception(
                        "Cannot read file: '%s' (permission denied)" % filepath
                    )

                # get filename and file size
                filename = os.path.basename(filepath)
                try:
                    filesize = os.path.getsize(filepath)
                except (OSError, IOError) as e:
                    raise Exception(
                        "Cannot get file size for '%s': %s" % (filepath, str(e))
                    )

                # find corresponding Attachment Name column for Attachment Location column
                attachmentLinkName = self._find_matching_name_for_column(
                    ctx, attachmentColumnCount, self.ATTACHMENTNAMES, actualDelimiter, i
                )

                # echo out attachment information including start page link
                attachmentLinkNameDisplay = ""
                if self.debug and attachmentLinkName != "":
                    attachmentLinkNameDisplay = ' -> "' + attachmentLinkName + '"'
                filesizeDisplay = self.group(filesize)
                if filesize > 999999 and not self.debug:
                    filesizeDisplay = (
                        filesizeDisplay[:-8] + "." + filesizeDisplay[-7:-5] + " MB"
                    )
                else:
                    filesizeDisplay += " bytes"
                self.echo(
                    "  Attachment: "
                    + filename
                    + " ("
                    + filesizeDisplay
                    + ")"
                    + attachmentLinkNameDisplay
                )

                thumbnailSelected = self._process_attachment_file(
                    item,
                    filepath,
                    filename,
                    filesize,
                    attachmentLinkName,
                    commandOptions,
                    testOnly,
                    n,
                    self.columnHeadings[n],
                    values[i].strip(),
                    thumbnails,
                    selectedThumbnail,
                    thumbnailSelected,
                )
        return thumbnailSelected

    def _process_raw_files(
        self, ctx, item, n, meta_value, actualDelimiter, attachmentColumnCount
    ):
        testOnly, meta = ctx.testOnly, ctx.meta
        # split for multi-value field
        values = meta_value.split(actualDelimiter)
        for i in range(len(values)):
            if values[i].strip() != "":
                uploadStatus = "   "
                attachIndent = ""

                # find corresponding Attachment Name column for Attachment Name column
                attachmentLinkName = self._find_matching_name_for_column(
                    ctx, attachmentColumnCount, self.ATTACHMENTNAMES, actualDelimiter, i
                )
                rawFiles = []

                # check if a folder rather than a file is specified
                if values[i].strip().endswith("*"):
                    uploadStatus = "     "
                    attachIndent = "  "
                    prependFolder = ""
                    targetDisplay = ""
                    if attachmentLinkName != "":
                        prependFolder = attachmentLinkName[:-1]
                        targetDisplay = " -> " + attachmentLinkName
                    self.echo("  Folder: " + values[i] + targetDisplay)

                    # recurse through the folder adding files to be uploaded
                    rootdir = os.path.normpath(os.path.join(
                        self.absoluteAttachmentsBasepath, values[i]
                    ).strip()[:-2])
                    for dirname, dirnames, filenames in os.walk(rootdir):
                        for filename in filenames:
                            rawFile = {}
                            rawFile["filepath"] = os.path.join(dirname, filename)
                            rawFile["originalfilename"] = os.path.relpath(
                                rawFile["filepath"], rootdir
                            ).replace("\\", "/")
                            rawFile["filename"] = (
                                prependFolder + rawFile["originalfilename"]
                            )
                            rawFile["filesize"] = os.path.getsize(rawFile["filepath"])
                            rawFiles.append(rawFile)
                else:
                    # a single file was specified so add that as the only file to be uploaded
                    rawFile = {}
                    rawFile["filepath"] = os.path.normpath(os.path.join(
                        self.absoluteAttachmentsBasepath, values[i]
                    ))
                    # ensure that attachment specified is not a directory
                    if os.path.isdir(rawFile["filepath"]):
                        raise Exception(rawFile["filepath"] + " is not a file")
                    rawFile["filename"] = os.path.basename(rawFile["filepath"])
                    rawFile["originalfilename"] = rawFile["filename"]
                    if attachmentLinkName != "":
                        rawFile["filename"] = attachmentLinkName
                    rawFile["filesize"] = os.path.getsize(rawFile["filepath"])
                    rawFiles.append(rawFile)

                # upload all raw files specified
                for rawFile in rawFiles:
                    # echo out attachment information including start page link
                    attachmentLinkNameDisplay = ""
                    if attachmentLinkName != "" and not values[i].strip().endswith("*"):
                        attachmentLinkNameDisplay = ' -> "' + attachmentLinkName + '"'
                    filesizeDisplay = self.group(rawFile["filesize"])
                    if rawFile["filesize"] > 999999 and not self.debug:
                        filesizeDisplay = (
                            filesizeDisplay[:-8] + "." + filesizeDisplay[-7:-5] + " MB"
                        )
                    else:
                        filesizeDisplay += " bytes"
                    self.echo(
                        attachIndent
                        + "  Attachment: "
                        + rawFile["originalfilename"]
                        + " ("
                        + filesizeDisplay
                        + ")"
                        + attachmentLinkNameDisplay
                    )

                    if not testOnly:
                        item.attachFile(
                            rawFile["filename"],
                            Utils.openFileForReading(rawFile["filepath"]),
                            uploadStatus,
                            self.chunkSize,
                        )

    def _setup_item_for_editing(
        self, ctx, createNewItem, itemID, itemVersion, commandOptions
    ):
        (
            tle,
            itemdefuuid,
            meta,
            collectionColumn,
            collectionIDs,
            urlsColumn,
            attachmentLocationsColumn,
            resourcesColumn,
            customAttachmentsColumn,
            sourceIdentifierColumn,
        ) = (
            ctx.tle,
            ctx.itemdefuuid,
            ctx.meta,
            ctx.collectionColumn,
            ctx.collectionIDs,
            ctx.urlsColumn,
            ctx.attachmentLocationsColumn,
            ctx.resourcesColumn,
            ctx.customAttachmentsColumn,
            ctx.sourceIdentifierColumn,
        )
        scriptAction = 0
        createNewVersion = False

        if createNewItem:
            collectionID = itemdefuuid
            if collectionColumn != -1:
                collectionName = meta[collectionColumn].strip()
                if collectionName != "":
                    collectionID = collectionIDs[collectionName]
                    self.echo("  Target collection: '%s'" % collectionName)

            item = tle.createNewItem(collectionID)
            itemID = item.uuid
            itemVersion = item.version
            item.prop.setNode("item/thumbnail", "default")
        else:
            if self.createNewVersions or "VERSION" in commandOptions:
                item = tle.newVersionItem(itemID, itemVersion)
                createNewVersion = True
                scriptAction = 1
                self.echo("  Creating new version")
            else:
                tle._forceUnlock(itemID, itemVersion)
                item = tle.editItem(itemID, itemVersion, "true")
                scriptAction = 2
                self.echo("  Editing item")

            if collectionColumn != -1 and meta[collectionColumn].strip() != "":
                self.echo(
                    "  Target collection: '%s'. Cannot use target collection for existing items (ignoring)"
                    % meta[collectionColumn].strip()
                )

            if (
                (
                    urlsColumn != -1
                    or attachmentLocationsColumn != -1
                    or resourcesColumn != -1
                    or customAttachmentsColumn != -1
                )
                and not self.appendAttachments
                and not "APPENDATTACH" in commandOptions
            ):
                item.deleteAttachments()
                item.prop.removeNode("item/itembody/packagefile")
                item.prop.removeNode("item/navigationNodes/node")

            if (
                self.existingMetadataMode not in [self.REPLACEMETA, self.APPENDMETA]
                and "APPENDMETA" not in commandOptions
                and "REPLACEMETA" not in commandOptions
            ):
                for childNode in item.prop.root.childNodes:
                    if childNode.nodeName == "item":
                        # use list() to iterate over a copy so we can remove elements safely
                        for itemChildNode in list(childNode.childNodes):
                            if itemChildNode.nodeName not in self.itemSystemNodes:
                                childNode.removeChild(itemChildNode)
                    else:
                        item.prop.root.removeChild(childNode)
            else:
                if sourceIdentifierColumn != -1:
                    if "@" not in self.columnHeadings[sourceIdentifierColumn]:
                        item.getXml().removeNode(
                            self.columnHeadings[sourceIdentifierColumn]
                        )

        return item, itemID, itemVersion, scriptAction, createNewVersion

    def _run_script(
        self, ctx, script_code, action, item_id, item_version, item, imsmanifest=None
    ):
        (
            row_counter,
            current_meta,
            test_only,
            tle,
            source_identifier_column,
            target_identifier_column,
            target_version_column,
        ) = (
            ctx.rowCounter,
            ctx.meta,
            ctx.testOnly,
            ctx.tle,
            ctx.sourceIdentifierColumn,
            ctx.targetIdentifierColumn,
            ctx.targetVersionColumn,
        )
        if not script_code.strip():
            return

        args = {
            "IMPORT": 0,
            "EXPORT": 1,
            "NEWITEM": 0,
            "NEWVERSION": 1,
            "EDITITEM": 2,
            "DELETEITEM": 3,
            "mode": 0,
            "action": action,
            "vars": self.scriptVariables,
            "rowData": current_meta,
            "rowCounter": row_counter,
            "testOnly": test_only,
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
            "sourceIdentifierIndex": source_identifier_column,
            "targetIdentifierIndex": target_identifier_column,
            "targetVersionIndex": target_version_column,
            "csvData": self.csvArray,
            "ebi": self.ebiScriptObject,
            "equella": tle,
        }

        if item:
            args.update(
                {
                    "itemId": item_id,
                    "itemVersion": item_version,
                    "xml": item.prop,
                    "xmldom": item.newDom,
                }
            )
        if imsmanifest:
            args["imsmanifest"] = imsmanifest

        try:
            exec(script_code, args)
        except Exception as e:
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
                scriptErrorMsg = "An error occured in the Script:\n%s (line %s)" % (
                    formattedException,
                    traceback.extract_tb(exceptionTraceback)[-1][1],
                )
                raise Exception(scriptErrorMsg)

    def _update_collaborators(
        self, item_id, item_version, item_xml, command_options, tle, collaborator_ids
    ):
        self.echo("  Setting collaborators")
        try:
            existingCollaboratorIDs = item_xml.getNodes(
                "item/collaborativeowners/collaborator"
            )

            if (
                self.existingMetadataMode != self.APPENDMETA
                and "APPENDMETA" not in command_options
            ):
                for existingCollaboratorID in existingCollaboratorIDs:
                    if existingCollaboratorID not in collaborator_ids:
                        tle.removeSharedOwner(
                            item_id, item_version, existingCollaboratorID
                        )

            for collaboratorID in collaborator_ids:
                if collaboratorID not in existingCollaboratorIDs:
                    tle.addSharedOwner(item_id, item_version, collaboratorID)

        except Exception as e:
            exactError = str(e)
            errorDebug = ""
            if self.debug:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
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

    def _process_columns(
        self, ctx, item, command_options, thumbnails, selected_thumbnail
    ):
        meta, itemdefuuid, collection_ids, test_only, source_identifier_column = (
            ctx.meta,
            ctx.itemdefuuid,
            ctx.collectionIDs,
            ctx.testOnly,
            ctx.sourceIdentifierColumn,
        )
        hyperlinkColumnCount = 0
        attachmentColumnCount = 0
        equellaResourceColumnCount = 0
        calHoldingMetadataTarget = ""
        thumbnailSelected = False

        for n in range(0, len(meta)):
            wx.GetApp().Yield()
            if self.StopProcessing:
                break

            isMetadataField = True
            if self.currentColumns[n][self.COLUMN_DELIMITER].strip() != "":
                actualDelimiter = self.currentColumns[n][self.COLUMN_DELIMITER].strip()
            else:
                actualDelimiter = "@~@~@~@~@~@~@"

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.URLS:
                hyperlinkColumnCount += 1
                isMetadataField = False
                self._process_urls(
                    ctx, item, n, ctx.meta[n], actualDelimiter, hyperlinkColumnCount
                )

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.ATTACHMENTLOCATIONS:
                attachmentColumnCount += 1
                isMetadataField = False
                thumbnailSelected = self._process_attachment_locations(
                    ctx,
                    item,
                    n,
                    ctx.meta[n],
                    actualDelimiter,
                    attachmentColumnCount,
                    command_options,
                    thumbnails,
                    selected_thumbnail,
                    thumbnailSelected,
                )

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.RAWFILES:
                attachmentColumnCount += 1
                isMetadataField = False
                self._process_raw_files(
                    ctx, item, n, ctx.meta[n], actualDelimiter, attachmentColumnCount
                )

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.EQUELLARESOURCES:
                equellaResourceColumnCount += 1
                isMetadataField = False
                calHoldingMetadataTarget = self._process_equella_resources(
                    ctx,
                    item,
                    n,
                    ctx.meta[n],
                    actualDelimiter,
                    equellaResourceColumnCount,
                    command_options,
                    calHoldingMetadataTarget,
                )

            if (
                self.currentColumns[n][self.COLUMN_DATATYPE] == self.CUSTOMATTACHMENTS
                and meta[n].strip() != ""
            ):
                isMetadataField = False
                thumbnailSelected = self._process_custom_attachments(
                    item, meta[n].strip(), self.columnHeadings[n], thumbnailSelected
                )

            isCustomAttachmentsColumn = self.currentColumns[n][
                self.COLUMN_DATATYPE
            ] == self.CUSTOMATTACHMENTS or (
                meta[n].strip().lower().startswith("<attachment")
                and "<type>" in meta[n].lower()
            )

            if (
                self.currentColumns[n][self.COLUMN_DATATYPE] == self.METADATA
                and not isCustomAttachmentsColumn
            ):
                self._process_metadata_column(
                    item, n, meta[n], command_options, actualDelimiter
                )

            if self.currentColumns[n][self.COLUMN_DATATYPE] == self.IGNORE:
                if self.currentColumns[n][self.COLUMN_DISPLAY] == "YES":
                    self.echo("  %s: %s" % (self.columnHeadings[n], meta[n].strip()))

        return calHoldingMetadataTarget

    def _handle_test_mode(self, ctx, item, cal_holding_target):
        row_counter = ctx.rowCounter
        # check to see if test XML files should be produced
        if self.saveTestXML:
            if cal_holding_target != "":
                self.addCALRelations(cal_holding_target, item.getXml())

            xmlFolderName = os.path.join(self.testItemfolder, self.sessionName)
            if not os.path.exists(xmlFolderName):
                os.makedirs(xmlFolderName)

            xmlFilename = os.path.join(xmlFolderName, "ebi-%06d.xml" % row_counter)

            with open(xmlFilename, "w") as fp:
                fp.write(item.newDom.toprettyxml("    ", "\n", self.encoding))

        # cancel edit (test only)
        item.parClient._cancelEdit(item.getUUID(), item.getVersion())
        self.echo("  Item valid for import")

    def _submit_item(
        self,
        ctx,
        item,
        cal_holding_target,
        create_new_item,
        create_new_version,
        command_options,
        saved_item_id,
        saved_item_version,
        owner_username,
        owner_id,
    ):
        owner_col, tle = ctx.ownerColumn, ctx.tle

        if cal_holding_target != "" and not (create_new_item or create_new_version):
            self.addCALRelations(cal_holding_target, item.getXml())

        bSubmit = 0
        statusMessage = " in draft status"
        if (create_new_item or create_new_version) and (
            not self.saveAsDraft and "DRAFT" not in command_options
        ):
            bSubmit = 1
            statusMessage = ""

        item.submit(bSubmit)
        self.tryPausing("[Paused]")

        # update owner if one specified and existing item being edited
        if (
            owner_col != -1
            and not create_new_version
            and not create_new_item
            and owner_id != ""
            and owner_username != ""
        ):
            self.echo("  Setting owner to '%s'" % owner_username)
            if item.getXml().getNode("item/owner") != owner_id:
                try:
                    tle.setOwner(saved_item_id, saved_item_version, owner_id)
                except Exception as e:
                    exactError = str(e)
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

        if create_new_item:
            self.echo(
                "  Item successfully imported%s (%s/%s)"
                % (statusMessage, saved_item_id, saved_item_version)
            )
        else:
            if create_new_version:
                self.echo("  New version successfully created" + statusMessage)
            else:
                self.echo("  Item successfully updated")

        # re-edit and add CAL holding relations metadata if necessary
        if (create_new_item or create_new_version) and cal_holding_target != "":
            self.echo("  Re-editing to add CAL metadata...")
            tle._forceUnlock(saved_item_id, saved_item_version)
            item = tle.editItem(saved_item_id, saved_item_version, "true")
            self.addCALRelations(cal_holding_target, item.getXml())
            item.submit(bSubmit)
            self.echo("  Item successfully updated")

    def _parse_thumbnail_settings(self, ctx):
        meta, thumbnails_col, selected_thumb_col = (
            ctx.meta,
            ctx.thumbnailsColumn,
            ctx.selectedThumbnailColumn,
        )
        thumbnails = []
        selected_thumbnail = ""

        if thumbnails_col != -1:
            thumbnail_delimiter = self.currentColumns[thumbnails_col][
                self.COLUMN_DELIMITER
            ].strip()
            if thumbnail_delimiter != "":
                thumbnails = meta[thumbnails_col].split(thumbnail_delimiter)
                thumbnails = [thumb.strip() for thumb in thumbnails]
            else:
                thumbnails = meta[thumbnails_col].strip()

        if selected_thumb_col != -1:
            selected_thumbnail = meta[selected_thumb_col].strip()

        return thumbnails, selected_thumbnail

    def _resolve_owner_and_collaborators(self, ctx, owner_username):
        meta, owner_col, collab_col = ctx.meta, ctx.ownerColumn, ctx.collaboratorsColumn
        owner_id = ""
        collaborator_ids = []
        all_rows_error = False

        # Resolve owner
        if owner_col != -1 and owner_username != "":
            self.echo("  Owner: " + owner_username)
            user_id, is_error = self._resolve_user_id(
                self.tle, owner_username, self.saveNonexistentUsernamesAsIDs
            )
            if is_error:
                self.echo(
                    "  ERROR: Cannot use Owner or Collaborators column datatypes with this version of EQUELLA",
                    style=2,
                )
                all_rows_error = True
                raise Exception(
                    "Cannot use Owner or Collaborators column datatypes with this version of EQUELLA"
                )
            if user_id:
                owner_id = user_id
            elif self.useEBIUsername:
                owner_col = -1
                self.echo("  '%s' not found so ignoring." % (owner_username))
            else:
                raise Exception("'%s' not found so cannot set owner." % owner_username)

        # Resolve collaborators
        if collab_col != -1 and meta[collab_col].strip() != "":
            actual_delimiter = "@~@~@~@~@~@~@"
            if self.currentColumns[collab_col][self.COLUMN_DELIMITER].strip() != "":
                actual_delimiter = self.currentColumns[collab_col][
                    self.COLUMN_DELIMITER
                ].strip()

            specified_collabs = meta[collab_col].split(actual_delimiter)
            self.echo("  Collaborators: " + ",".join(specified_collabs))
            for collab in specified_collabs:
                collab_name = collab.strip()
                user_id, is_error = self._resolve_user_id(
                    self.tle, collab_name, self.saveNonexistentUsernamesAsIDs
                )
                if is_error:
                    self.echo(
                        "  ERROR: Cannot use Owner or Collaborators column datatypes with this version of EQUELLA",
                        style=2,
                    )
                    all_rows_error = True
                    raise Exception(
                        "Cannot use Owner or Collaborators column datatypes with this version of EQUELLA"
                    )
                if user_id:
                    collaborator_ids.append(user_id)
                elif self.ignoreNonexistentCollaborators:
                    self.echo(
                        "  '%s' not found so ignoring that collaborator." % collab_name
                    )
                else:
                    raise Exception(
                        "'%s' not found so cannot set collaborators." % collab_name
                    )

        return owner_id, collaborator_ids, all_rows_error

    def _get_default_state(self):
        return {
            "createNewItem": True,
            "createNewVersion": False,
            "allRowsError": False,
            "itemID": "nil",
            "itemVersion": 0,
            "savedItemID": "",
            "savedItemVersion": "",
            "n": -1,
            "attemptingUpload": False,
            "imsmanifest": None,
        }

    def _clean_data(self, meta, ownerColumn, commandOptionsColumn, targetVersionColumn):
        ownerUsername = meta[ownerColumn].strip()
        commandOptions = []
        if commandOptionsColumn != -1:
            tempCommandOptions = [
                commandOption.strip().upper()
                for commandOption in meta[commandOptionsColumn].split(",")
            ]
            commandOptions = [cmd for cmd in tempCommandOptions if cmd != ""]

        itemVersion = 0
        if targetVersionColumn != -1 and meta[targetVersionColumn].strip() != "":
            try:
                itemVersion = int(meta[targetVersionColumn].strip())
                if itemVersion < -1:
                    raise Exception("Invalid item version specified")
            except ValueError:
                raise Exception("Invalid item version specified")

        return ownerUsername, commandOptions, itemVersion

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

        Processes metadata, attachments, URLs, and resources for one row, handling:
        - Item creation or update based on identifiers
        - Attachment processing (files, URLs, EQUELLA resources, custom XML)
        - Unzip commands for archive extraction
        - Metadata replacement/append modes
        - User/collaborator resolution

        This refactored process isolates business logic away from the GUI Engine.
        Large method parameter structures are bundled natively inside a `RowContext`
        pattern for readability and to prevent `__setattr__` and `__getattr__` side effects
        from iterations.

        Returns tuple: (itemID, itemVersion, error_message)
        """

        ctx = RowContext(
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

        failCount = 0
        retriesDone = False

        # loop for retrying if network errors occur
        while not retriesDone:
            try:
                wx.GetApp().Yield()
                state = self._get_default_state()
                createNewItem = state["createNewItem"]
                createNewVersion = state["createNewVersion"]
                allRowsError = state["allRowsError"]
                itemID = state["itemID"]
                itemVersion = state["itemVersion"]
                savedItemID = state["savedItemID"]
                savedItemVersion = state["savedItemVersion"]
                n = state["n"]
                attemptingUpload = state["attemptingUpload"]
                imsmanifest = state["imsmanifest"]

                if self.Skip:
                    self.echo("  Row skipped")
                    return "", "", "", [], ""

                ownerUsername, commandOptions, extractedItemVersion = self._clean_data(
                    meta, ownerColumn, commandOptionsColumn, targetVersionColumn
                )
                if extractedItemVersion != 0:
                    itemVersion = extractedItemVersion

                ownerID, collaboratorIDs, allRowsError = (
                    self._resolve_owner_and_collaborators(ctx, ownerUsername)
                )

                if len(commandOptions) > 0:
                    self.echo("  Command options: " + ",".join(commandOptions))
                # if Source Identifier column specified check if item exists by sourceIdentifier
                if sourceIdentifierColumn != -1:
                    itemID, itemVersion, createNewItem = self._find_existing_item(
                        ctx, itemVersion
                    )
                # if Target Identifier column specified edit item by ID (using latest version of item)
                if (
                    targetIdentifierColumn != -1
                    and meta[targetIdentifierColumn].strip() != ""
                ):
                    itemID = meta[targetIdentifierColumn].strip()

                    self.echo("  Target identifier = " + itemID)
                    if (
                        targetVersionColumn != -1
                        and meta[targetVersionColumn].strip() != ""
                    ):
                        self.echo(
                            "  Target version = " + meta[targetVersionColumn].strip()
                        )

                    # try getting item
                    foundItem = tle.getItem(itemID, itemVersion)

                    self.echo(
                        "  Item exists in EQUELLA ("
                        + itemID
                        + "/"
                        + foundItem.getNode("item/@version")
                        + ")"
                    )
                    createNewItem = False

                if "DELETE" in commandOptions:
                    # check that if using target identifiers is specified that this row has one
                    if (
                        targetIdentifierColumn != -1
                        and meta[targetIdentifierColumn].strip() == ""
                        and sourceIdentifierColumn == -1
                    ):
                        raise Exception(
                            "Neither source identifer nor target identifier supplied"
                        )
                    # run Row Pre-Script
                    self._run_script(ctx, self.preScript, 3, None, None, None)
                    if not createNewItem:
                        if not testOnly:
                            # delete existing item
                            tle._forceUnlock(itemID, itemVersion)
                            tle._deleteItem(itemID, itemVersion)
                            self.echo("  Item successfully deleted")

                            savedItemID = itemID
                            savedItemVersion = itemVersion
                        else:
                            self.echo("  Item valid to delete")

                    self.successCount += 1

                else:
                    scriptAction = 0

                    # create new item or prepare existing one
                    item, itemID, itemVersion, scriptAction, createNewVersion = (
                        self._setup_item_for_editing(
                            ctx, createNewItem, itemID, itemVersion, commandOptions
                        )
                    )

                    # run Row Pre-Script
                    self._run_script(
                        ctx, self.preScript, scriptAction, itemID, itemVersion, item
                    )
                    thumbnails, selectedThumbnail = self._parse_thumbnail_settings(ctx)

                    calHoldingMetadataTarget = self._process_columns(
                        ctx, item, commandOptions, thumbnails, selectedThumbnail
                    )

                    # set selected thumbnail to none if applicable
                    if selectedThumbnail != "":
                        if selectedThumbnail.upper() == "NONE":
                            item.getXml().setNode("item/thumbnail", "none")

                    # if necesary set owner and collaborators for new items and new versions
                    if createNewVersion or createNewItem:
                        if ownerColumn != -1 and ownerUsername != "":

                            # add owner to new item/version
                            item.getXml().setNode("item/owner", ownerID)

                        if collaboratorsColumn != -1:

                            # NOTE: EQUELLA automatically clears out collaborators when
                            # creating new versions so this is actually unneccesary. Not
                            # actually possible to "append" collaborators to a new version.
                            if (
                                self.existingMetadataMode != self.APPENDMETA
                                and "APPENDMETA" not in commandOptions
                            ):
                                item.getXml().removeNode(
                                    "item/collaborativeowners/collaborator"
                                )

                            # add collaborators to new item/version
                            for collaboratorID in collaboratorIDs:
                                item.getXml().createNode(
                                    "item/collaborativeowners/collaborator",
                                    collaboratorID,
                                )

                    # ##############################
                    # submit item or cancel editing
                    # ##############################
                    n = -1
                    wx.GetApp().Yield()
                    if not self.StopProcessing:
                        savedItemID = item.getUUID()
                        savedItemVersion = item.getVersion()

                        # run Row Post-Script
                        self._run_script(
                            ctx,
                            self.postScript,
                            scriptAction,
                            savedItemID,
                            savedItemVersion,
                            item,
                            imsmanifest,
                        )

                    if not self.StopProcessing and not self.Skip:
                        if testOnly:
                            self._handle_test_mode(ctx, item, calHoldingMetadataTarget)
                        else:
                            self._submit_item(
                                ctx,
                                item,
                                calHoldingMetadataTarget,
                                createNewItem,
                                createNewVersion,
                                commandOptions,
                                savedItemID,
                                savedItemVersion,
                                ownerUsername,
                                ownerID,
                            )
                        self.successCount += 1
                    else:
                        item.parClient._cancelEdit(item.getUUID(), item.getVersion())
                        if self.Skip:
                            self.echo("  Row skipped")

                retriesDone = True

                # return Item ID, Item Version and Source Identifier
                sourceIdentifier = ""
                if sourceIdentifierColumn != -1:
                    sourceIdentifier = meta[sourceIdentifierColumn].strip()
                return savedItemID, savedItemVersion, sourceIdentifier, meta, ""

            except Exception as e:
                exactError = str(e)

                # check if it is worthwhile recycling the session and retrying
                if failCount < self.maxRetry and (
                    "(10054)" in exactError
                    or "(10060)" in exactError
                    or "(10061)" in exactError
                    or "(104)" in exactError
                ):
                    failCount += 1
                    self.echo("  %s. Retrying..." % (exactError))

                    # pause for increasing periods with each fail. 5 seconds, 10 seconds, 15 seconds... so on until maximum number of retries
                    time.sleep(5 * failCount)
                    try:
                        item.parClient._cancelEdit(item.getUUID(), item.getVersion())
                    except Exception as e:
                        pass
                    self.tle = None
                    self.tle = TLEClient(
                        self,
                        self.institutionUrl,
                        self.username,
                        self.password,
                        self.proxy,
                        self.proxyUsername,
                        self.proxyPassword,
                        self.debug,
                    )

                else:
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

                    if "Collection not found" in exactError:
                        allRowsError = True

                    # add further information if error is with a particular column etc
                    actionError = ""
                    if n != -1 and not attemptingUpload:
                        actionError = " parsing column %s '%s'" % (
                            n + 1,
                            str(self.columnHeadings[n]),
                        )
                    if attemptingUpload:
                        actionError = " uploading file"
                        attemptingUpload = False

                    self.echo(
                        time.strftime("%H:%M:%S: ", time.localtime(time.time()))
                        + "ERROR%s: %s%s"
                        % (str(actionError), str(exactError), str(errorDebug)),
                        style=2,
                    )

                    # halt processing if the error will apply to all rows
                    if allRowsError:
                        raise Exception("Halting process")
                    # return Item ID, Item Version and Source Identifier
                    sourceIdentifier = ""
                    if sourceIdentifierColumn != -1:
                        sourceIdentifier = meta[sourceIdentifierColumn].strip()

                    return (
                        savedItemID,
                        savedItemVersion,
                        sourceIdentifier,
                        meta,
                        "ERROR%s: %s%s"
                        % (str(actionError), str(exactError), str(errorDebug)),
                    )
