"""REST transport scaffold for EBI client compatibility.

This module provides the same top-level symbols expected by the importer,
while REST method implementations are completed incrementally.
"""

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from binascii import a2b_base64
from http.cookiejar import CookieJar
from io import BytesIO
from urllib.parse import urlparse
from zipfile import ZipFile

from xml.dom.minidom import Document, parseString

from equellaclient41 import NewItemClient, PropBagEx


class TLEClient:
    """REST-based client with legacy-compatible public method names.

    The importer calls the historical TLEClient surface directly. This class
    preserves those method names so Engine/RowProcessor do not need a large
    rewrite during migration.
    """

    def __init__(
        self,
        owner,
        institutionUrl,
        username,
        password,
        proxy="",
        proxyusername="",
        proxypassword="",
        debug=False,
        sso=0,
    ):
        self.owner = owner
        self.debug = debug
        self.username = username
        self.password = password
        self.proxy = proxy
        self.proxyusername = proxyusername
        self.proxypassword = proxypassword

        self.institutionUrl = institutionUrl
        urlLogonPagePos = self.institutionUrl.find("/logon.do")
        if urlLogonPagePos != -1:
            self.institutionUrl = self.institutionUrl[:urlLogonPagePos]
        if self.institutionUrl.endswith("/"):
            self.institutionUrl = self.institutionUrl[:-1]

        parsed = urlparse(self.institutionUrl)
        self.protocol = parsed.scheme
        self.host = parsed.netloc
        self.context = parsed.path

        self._ssl_context = ssl._create_unverified_context()
        self._cookie_jar = CookieJar()

        handlers = [
            urllib.request.HTTPCookieProcessor(self._cookie_jar),
            urllib.request.HTTPSHandler(context=self._ssl_context),
        ]
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}))
            if self.proxyusername or self.proxypassword:
                password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                password_mgr.add_password(
                    None, self.proxy, self.proxyusername, self.proxypassword
                )
                handlers.append(urllib.request.ProxyBasicAuthHandler(password_mgr))

        self._opener = urllib.request.build_opener(*handlers)
        urllib.request.install_opener(self._opener)

        self._rest_access_token = os.environ.get("EBI_REST_ACCESS_TOKEN", "").strip()
        self._rest_admin_token = os.environ.get("EBI_REST_ADMIN_TOKEN", "").strip()

        self._sessions = {}
        self._upload_buffers = {}
        self._collection_createable = {}
        self._collection_name_by_uuid = {}
        self._createable_collection_uuids = None

        # Prefer explicit token auth when provided. This supports SSO-only sites
        # where credential form-post login endpoints are unavailable.
        if not (self._rest_access_token or self._rest_admin_token):
            self._establish_cookie_session()

    def _not_implemented(self, method):
        raise NotImplementedError(
            "REST client method not implemented yet: %s" % method
        )

    def _build_auth_headers(self):
        headers = {"Accept": "application/json"}
        if self._rest_access_token:
            headers["X-Authorization"] = "access_token=%s" % self._rest_access_token
        elif self._rest_admin_token:
            headers["X-Authorization"] = "admin_token=%s" % self._rest_admin_token
        return headers

    def _has_session_cookie(self):
        for cookie in self._cookie_jar:
            if cookie.name and cookie.name.upper().startswith("JSESSIONID"):
                return True
        return False

    def _establish_cookie_session(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml",
        }

        # Try modern form-post flow first (institution root), then legacy endpoints.
        login_attempts = [
            (
                self.institutionUrl + "/",
                {
                    "username": self.username,
                    "password": self.password,
                },
            ),
            (
                self.institutionUrl + "/j_spring_security_check",
                {
                    "j_username": self.username,
                    "j_password": self.password,
                },
            ),
            (
                self.institutionUrl + "/j_security_check",
                {
                    "j_username": self.username,
                    "j_password": self.password,
                },
            ),
            (
                self.institutionUrl + "/security/login",
                {
                    "j_username": self.username,
                    "j_password": self.password,
                },
            ),
        ]

        attempted = []
        last_error = None
        for login_url, form_data in login_attempts:
            attempted.append(login_url)
            request = urllib.request.Request(
                login_url,
                data=urllib.parse.urlencode(form_data).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                response = self._opener.open(request)
                final_url = ""
                try:
                    final_url = response.geturl() or ""
                except Exception:
                    final_url = ""
                response.read()

                # Accept standard session cookie, or successful home redirect patterns.
                if self._has_session_cookie() or "home.do" in final_url:
                    return

                # If call succeeded but did not establish a session, continue probing.
                last_error = "No session cookie returned by %s" % login_url
            except urllib.error.HTTPError as exc:
                last_error = "HTTP %s at %s" % (exc.code, login_url)
                # 404 means endpoint missing; try next known endpoint.
                if exc.code == 404:
                    continue
                raise Exception("REST login failed: %s" % last_error)
            except Exception as exc:
                raise Exception("REST login failed at %s: %s" % (login_url, str(exc)))

        detail = last_error if last_error else "No login endpoint responded"
        raise Exception(
            "REST login failed. Attempted endpoints: %s. Last error: %s. "
            "If this institution uses SSO or does not expose credential login endpoints, "
            "set EBI_REST_ACCESS_TOKEN or EBI_REST_ADMIN_TOKEN."
            % (", ".join(attempted), detail)
        )

    def _request(
        self,
        method,
        path,
        params=None,
        body=None,
        headers=None,
        raw=False,
        include_response_meta=False,
    ):
        url = self.institutionUrl + path
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = url + ("&" if "?" in url else "?") + query

        req_headers = self._build_auth_headers()
        if headers:
            req_headers.update(headers)

        data = None
        if body is not None:
            req_headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            response = self._opener.open(request)
            payload = response.read()
            response_status = None
            try:
                response_status = response.getcode()
            except Exception:
                response_status = None

            response_location = ""
            try:
                response_location = response.headers.get("Location", "")
            except Exception:
                response_location = ""

            if raw:
                return payload
            if not payload:
                if include_response_meta:
                    return {
                        "_status": response_status,
                        "_location": response_location,
                    }
                return None
            decoded = json.loads(payload.decode("utf-8"))
            if include_response_meta and isinstance(decoded, dict):
                decoded.setdefault("_status", response_status)
                decoded.setdefault("_location", response_location)
            return decoded
        except urllib.error.HTTPError as exc:
            details = ""
            try:
                details = exc.read().decode("utf-8")
            except Exception:
                pass
            if details:
                raise Exception("REST %s %s failed: HTTP %s - %s" % (method, path, exc.code, details))
            raise Exception("REST %s %s failed: HTTP %s" % (method, path, exc.code))

    def _item_identity_from_location(self, location):
        if not location:
            return "", ""

        parsed = urlparse(location)
        path = parsed.path or str(location)

        marker = "/api/item/"
        marker_pos = path.find(marker)
        if marker_pos == -1:
            return "", ""

        tail = path[marker_pos + len(marker):].strip("/")
        parts = tail.split("/")
        if len(parts) < 2:
            return "", ""

        return parts[0], parts[1]

    def _attachment_to_xml(self, doc, attachment_json):
        attachment = doc.createElement("attachment")

        atype = attachment_json.get("type", "")
        if atype == "file":
            attachment.setAttribute("type", "local")
            file_node = doc.createElement("file")
            file_node.appendChild(doc.createTextNode(attachment_json.get("filename", "")))
            attachment.appendChild(file_node)
        elif atype == "url":
            attachment.setAttribute("type", "remote")
            file_node = doc.createElement("file")
            file_node.appendChild(doc.createTextNode(attachment_json.get("url", "")))
            attachment.appendChild(file_node)
        elif atype == "linked-resource":
            attachment.setAttribute("type", "custom")
            type_node = doc.createElement("type")
            type_node.appendChild(doc.createTextNode("resource"))
            attachment.appendChild(type_node)
            file_node = doc.createElement("file")
            file_node.appendChild(doc.createTextNode(attachment_json.get("resourcePath", "")))
            attachment.appendChild(file_node)
        elif atype == "scorm":
            attachment.setAttribute("type", "custom")
            type_node = doc.createElement("type")
            type_node.appendChild(doc.createTextNode("scorm"))
            attachment.appendChild(type_node)
            file_node = doc.createElement("file")
            file_node.appendChild(doc.createTextNode(attachment_json.get("packageFile", "")))
            attachment.appendChild(file_node)
        elif atype == "zip":
            attachment.setAttribute("type", "custom")
            type_node = doc.createElement("type")
            type_node.appendChild(doc.createTextNode("zip"))
            attachment.appendChild(type_node)
            file_node = doc.createElement("file")
            file_node.appendChild(doc.createTextNode(attachment_json.get("folder", "")))
            attachment.appendChild(file_node)
        elif atype in ("package-res", "scorm-res"):
            attachment.setAttribute("type", "local")
            file_node = doc.createElement("file")
            file_node.appendChild(doc.createTextNode(attachment_json.get("filename", "")))
            attachment.appendChild(file_node)
        else:
            attachment.setAttribute("type", "custom")

        for key, value in (("uuid", attachment_json.get("uuid")), ("description", attachment_json.get("description"))):
            if value:
                node = doc.createElement(key)
                node.appendChild(doc.createTextNode(str(value)))
                attachment.appendChild(node)

        return attachment

    def _child_text(self, parent, name, default=""):
        matches = [n for n in parent.childNodes if getattr(n, "tagName", None) == name]
        if not matches:
            return default
        node = matches[0]
        if node.firstChild is None:
            return default
        return node.firstChild.nodeValue

    def _item_json_to_propbag(self, item_json):
        metadata = item_json.get("metadata", "<xml><item/></xml>")
        try:
            metadata_doc = parseString(metadata.encode("utf-8"))
        except Exception:
            metadata_doc = Document()
            xml_node = metadata_doc.createElement("xml")
            metadata_doc.appendChild(xml_node)
            item_node = metadata_doc.createElement("item")
            xml_node.appendChild(item_node)
        else:
            root = metadata_doc.documentElement
            if root.tagName == "xml":
                xml_node = root
                item_nodes = [n for n in xml_node.childNodes if getattr(n, "tagName", None) == "item"]
                if item_nodes:
                    item_node = item_nodes[0]
                else:
                    item_node = metadata_doc.createElement("item")
                    xml_node.appendChild(item_node)
            elif root.tagName == "item":
                item_node = root
                xml_node = metadata_doc.createElement("xml")
                metadata_doc.removeChild(root)
                metadata_doc.appendChild(xml_node)
                xml_node.appendChild(item_node)
            else:
                xml_node = metadata_doc.createElement("xml")
                metadata_doc.appendChild(xml_node)
                item_node = metadata_doc.createElement("item")
                xml_node.appendChild(item_node)

        if item_json.get("uuid"):
            item_node.setAttribute("id", str(item_json.get("uuid")))
        if item_json.get("version") is not None:
            item_node.setAttribute("version", str(item_json.get("version")))

        collection_uuid = ((item_json.get("collection") or {}).get("uuid"))
        if collection_uuid:
            item_node.setAttribute("itemdefid", str(collection_uuid))

        attachments_parent = None
        existing = item_node.getElementsByTagName("attachments")
        if existing:
            attachments_parent = existing[0]
            for child in list(attachments_parent.childNodes):
                attachments_parent.removeChild(child)
        else:
            attachments_parent = metadata_doc.createElement("attachments")
            item_node.appendChild(attachments_parent)

        # Keep IMS package metadata in the legacy XML shape expected by Engine.
        itembody_nodes = item_node.getElementsByTagName("itembody")
        if itembody_nodes:
            itembody = itembody_nodes[0]
        else:
            itembody = metadata_doc.createElement("itembody")
            item_node.appendChild(itembody)

        for child in list(itembody.childNodes):
            if getattr(child, "tagName", None) == "packagefile":
                itembody.removeChild(child)

        for attachment_json in item_json.get("attachments", []):
            if attachment_json.get("type") == "package":
                package_node = metadata_doc.createElement("packagefile")
                package_file = attachment_json.get("packageFile", "")
                package_node.appendChild(metadata_doc.createTextNode(package_file))
                if attachment_json.get("description"):
                    package_node.setAttribute("name", str(attachment_json.get("description")))
                if attachment_json.get("size") is not None:
                    package_node.setAttribute("size", str(attachment_json.get("size")))
                if attachment_json.get("uuid"):
                    package_node.setAttribute("uuid", str(attachment_json.get("uuid")))
                package_node.setAttribute("stored", "true")
                itembody.appendChild(package_node)

            attachments_parent.appendChild(self._attachment_to_xml(metadata_doc, attachment_json))

        return PropBagEx(xml_node)

    def _item_json_to_document(self, item_json, file_uuid=""):
        prop = self._item_json_to_propbag(item_json)
        if file_uuid:
            prop.setNode("item/staging", file_uuid)
        return prop.document

    def _xml_to_item_json(self, xml_text):
        dom = parseString(xml_text.encode("utf-8"))
        root = dom.documentElement

        if root.tagName == "xml":
            xml_node = root
            item_nodes = [n for n in xml_node.childNodes if getattr(n, "tagName", None) == "item"]
            if not item_nodes:
                raise Exception("Invalid item XML: missing item node")
            item_node = item_nodes[0]
            metadata_xml = xml_node.toxml()
        elif root.tagName == "item":
            item_node = root
            metadata_xml = "<xml>" + root.toxml() + "</xml>"
        else:
            raise Exception("Invalid item XML root: %s" % root.tagName)

        item_json = {
            "metadata": metadata_xml,
            "attachments": [],
        }

        item_id = item_node.getAttribute("id")
        if item_id:
            item_json["uuid"] = item_id

        item_version = item_node.getAttribute("version")
        if item_version != "":
            try:
                item_json["version"] = int(item_version)
            except ValueError:
                item_json["version"] = item_version

        itemdefid = item_node.getAttribute("itemdefid")
        if itemdefid:
            item_json["collection"] = {"uuid": itemdefid}

        owner_nodes = [n for n in item_node.childNodes if getattr(n, "tagName", None) == "owner"]
        if owner_nodes and owner_nodes[0].firstChild is not None:
            item_json["owner"] = {"id": owner_nodes[0].firstChild.nodeValue}

        collaborators = []
        for collab in item_node.getElementsByTagName("collaborator"):
            if collab.firstChild is not None:
                collaborators.append({"id": collab.firstChild.nodeValue})
        if collaborators:
            item_json["collaborators"] = collaborators

        staging = ""
        staging_nodes = [n for n in item_node.childNodes if getattr(n, "tagName", None) == "staging"]
        if staging_nodes and staging_nodes[0].firstChild is not None:
            staging = staging_nodes[0].firstChild.nodeValue

        for attachment in item_node.getElementsByTagName("attachment"):
            atype = attachment.getAttribute("type")
            file_value = self._child_text(attachment, "file", "")
            description = self._child_text(attachment, "description", "")
            attach_uuid = self._child_text(attachment, "uuid", "")

            if atype == "local":
                rest_attachment = {
                    "type": "file",
                    "filename": file_value,
                    "description": description,
                }
            elif atype == "remote":
                rest_attachment = {
                    "type": "url",
                    "url": file_value,
                    "description": description,
                }
            elif atype == "custom" and self._child_text(attachment, "type", "") == "resource":
                item_uuid = ""
                item_version_value = 1
                resource_type = "p"
                entries = attachment.getElementsByTagName("entry")
                for entry in entries:
                    strings = entry.getElementsByTagName("string")
                    ints = entry.getElementsByTagName("int")
                    if len(strings) >= 2:
                        key = strings[0].firstChild.nodeValue if strings[0].firstChild else ""
                        value = strings[1].firstChild.nodeValue if strings[1].firstChild else ""
                        if key == "uuid":
                            item_uuid = value
                        elif key == "type":
                            resource_type = value
                    if len(strings) >= 1 and strings[0].firstChild and strings[0].firstChild.nodeValue == "version" and len(ints) >= 1 and ints[0].firstChild:
                        try:
                            item_version_value = int(ints[0].firstChild.nodeValue)
                        except ValueError:
                            item_version_value = 1

                rest_attachment = {
                    "type": "linked-resource",
                    "itemUuid": item_uuid,
                    "itemVersion": item_version_value,
                    "resourceType": resource_type,
                    "resourcePath": file_value,
                    "description": description,
                }
            elif atype == "custom" and self._child_text(attachment, "type", "") == "scorm":
                rest_attachment = {
                    "type": "scorm",
                    "description": description,
                    "packageFile": file_value,
                }
            elif atype == "custom" and self._child_text(attachment, "type", "") == "zip":
                rest_attachment = {
                    "type": "zip",
                    "description": description,
                    "folder": file_value,
                }
            else:
                if atype == "local":
                    zip_parent = ""
                    for entry in attachment.getElementsByTagName("entry"):
                        strings = entry.getElementsByTagName("string")
                        if len(strings) >= 2:
                            key = strings[0].firstChild.nodeValue if strings[0].firstChild else ""
                            value = strings[1].firstChild.nodeValue if strings[1].firstChild else ""
                            if key == "ZIP_ATTACHMENT_UUID":
                                zip_parent = value
                                break
                    if zip_parent:
                        rest_attachment = {
                            "type": "package-res",
                            "filename": file_value,
                            "description": description,
                        }
                    else:
                        rest_attachment = {
                            "type": "file",
                            "filename": file_value,
                            "description": description,
                        }
                else:
                    # Unsupported attachment types are skipped for now.
                    continue

            if attach_uuid:
                rest_attachment["uuid"] = attach_uuid
            item_json["attachments"].append(rest_attachment)

        # Include IMS package attachment if represented via itembody/packagefile.
        for package_node in item_node.getElementsByTagName("packagefile"):
            package_file = package_node.firstChild.nodeValue if package_node.firstChild else ""
            if not package_file:
                continue
            package_attachment = {
                "type": "package",
                "packageFile": package_file,
                "description": package_node.getAttribute("name") or package_file,
            }
            if package_node.getAttribute("uuid"):
                package_attachment["uuid"] = package_node.getAttribute("uuid")
            if package_node.getAttribute("size"):
                try:
                    package_attachment["size"] = int(package_node.getAttribute("size"))
                except ValueError:
                    pass

            duplicate = False
            for existing in item_json["attachments"]:
                if (
                    existing.get("type") == "package"
                    and existing.get("packageFile") == package_attachment.get("packageFile")
                ):
                    duplicate = True
                    break
            if not duplicate:
                item_json["attachments"].append(package_attachment)

        return item_json, staging

    def _resolve_item_version(self, itemversion):
        if str(itemversion) in ("0", "", "None"):
            return "latest"
        return str(itemversion)

    def _get_item_json(self, itemid, itemversion, info="all"):
        version = self._resolve_item_version(itemversion)
        params = {"info": info} if info else None
        return self._request("GET", "/api/item/%s/%s" % (itemid, version), params=params)

    def _put_item_json(self, itemid, itemversion, item_json):
        version = self._resolve_item_version(itemversion)
        return self._request("PUT", "/api/item/%s/%s" % (itemid, version), body=item_json)

    def _create_file_area(self):
        payload = self._request("POST", "/api/file") or {}
        file_uuid = payload.get("uuid")
        if not file_uuid:
            raise Exception("REST file area creation returned no UUID")
        return file_uuid

    def _copy_file_area(self, itemid, itemversion):
        payload = self._request(
            "POST",
            "/api/file/copy",
            params={"uuid": itemid, "version": itemversion},
        ) or {}
        file_uuid = payload.get("uuid")
        if not file_uuid:
            raise Exception("REST file area copy returned no UUID")
        return file_uuid

    def _session_key(self, itemid, itemversion):
        return (str(itemid), str(itemversion))

    def _store_session(self, itemid, itemversion, **data):
        self._sessions[self._session_key(itemid, itemversion)] = data

    def _get_session(self, itemid, itemversion):
        return self._sessions.get(self._session_key(itemid, itemversion))

    def _pop_session(self, itemid, itemversion):
        return self._sessions.pop(self._session_key(itemid, itemversion), None)

    def _upload_binary(self, file_area_uuid, path, data):
        encoded_path = urllib.parse.quote(path.lstrip("/"), safe="/")
        request = urllib.request.Request(
            self.institutionUrl + "/api/file/%s/content/%s" % (file_area_uuid, encoded_path),
            data=data,
            headers=self._build_auth_headers(),
            method="PUT",
        )
        request.add_header("Content-Type", "application/octet-stream")
        try:
            self._opener.open(request).read()
        except urllib.error.HTTPError as exc:
            raise Exception("REST upload failed: HTTP %s" % exc.code)

    def _uploadFile(self, stagingid, filename, data, overwrite):
        key = (str(stagingid), str(filename))
        is_first_chunk = str(overwrite).lower() == "true"
        if is_first_chunk or key not in self._upload_buffers:
            self._upload_buffers[key] = bytearray()

        try:
            self._upload_buffers[key].extend(a2b_base64(data))
        except Exception:
            raise Exception("Invalid base64 data supplied to REST upload")

        # NewItemClient uploads in chunks; re-upload current aggregate so the last
        # chunk results in a complete file in the file area.
        self._upload_binary(stagingid, filename, bytes(self._upload_buffers[key]))

    def _unzipFile(self, stagingid, zipfile, outpath):
        key = (str(stagingid), str(zipfile))
        zipped = self._upload_buffers.get(key)
        if not zipped:
            raise Exception("ZIP content not available for unzip: %s" % zipfile)

        prefix = outpath.strip("/")
        with ZipFile(BytesIO(bytes(zipped))) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                member_name = member.filename.replace("\\", "/")
                target_path = prefix + "/" + member_name if prefix else member_name
                data = zf.read(member)
                self._upload_binary(stagingid, target_path, data)

        return None

    def _deleteAttachmentFile(self, stagingid, filename):
        if not filename:
            return None
        encoded_path = urllib.parse.quote(filename.lstrip("/"), safe="/")
        self._request("DELETE", "/api/file/%s/content/%s" % (stagingid, encoded_path))
        return None

    def _stopEdit(self, xml, submit):
        item_json, staging = self._xml_to_item_json(xml)

        itemid = item_json.get("uuid")
        itemversion = item_json.get("version")
        if not itemid or itemversion is None:
            raise Exception("Cannot save item: missing UUID/version")

        session = self._get_session(itemid, itemversion) or {}
        file_uuid = staging or session.get("file_uuid")

        put_params = {}
        if file_uuid:
            put_params["file"] = file_uuid
        lock_uuid = session.get("lock_uuid", "")
        if lock_uuid:
            put_params["lock"] = lock_uuid

        if put_params:
            self._request(
                "PUT",
                "/api/item/%s/%s" % (itemid, itemversion),
                params=put_params,
                body=item_json,
            )
        else:
            self._put_item_json(itemid, itemversion, item_json)

        if str(submit).lower() == "true":
            self._request("POST", "/api/item/%s/%s/action/submit" % (itemid, itemversion))

        if session:
            session["submitted"] = True
            self._store_session(itemid, itemversion, **session)

    def _cancelEdit(self, itemid, itemversion, *unused):
        session = self._pop_session(itemid, itemversion)
        if not session:
            return None

        lock_uuid = session.get("lock_uuid")
        if lock_uuid:
            try:
                self._request("DELETE", "/api/item/%s/%s/lock" % (itemid, itemversion))
            except Exception:
                pass

        if session.get("created_draft") and not session.get("submitted"):
            try:
                self._request("DELETE", "/api/item/%s/%s" % (itemid, itemversion))
            except Exception:
                pass

        return None

    def logout(self):
        return None

    def getFile(self, url, filepath):
        request = urllib.request.Request(url, headers=self._build_auth_headers(), method="GET")
        try:
            response = self._opener.open(request)
            data = response.read()
        except urllib.error.HTTPError as exc:
            raise Exception("REST file download failed: HTTP %s" % exc.code)

        with open(filepath, "wb") as f:
            f.write(data)

        return {}

    def getText(self, url):
        request = urllib.request.Request(url, headers=self._build_auth_headers(), method="GET")
        try:
            response = self._opener.open(request)
            data = response.read()
        except urllib.error.HTTPError as exc:
            raise Exception("REST text fetch failed: HTTP %s" % exc.code)
        return data.decode("utf-8")

    def _enumerateItemDefs(self, forExport=False):
        discover_map = self._get_collections_by_privilege("DISCOVER_ITEM")

        # For import mode, allow broader collection listing while still enforcing
        # create rights later at createNewItem time.
        if not forExport:
            create_map = self._get_collections_by_privilege("CREATE_ITEM")
            create_set = set(create_map.keys())

            self._collection_createable = {
                uuid: (uuid in create_set) for uuid in discover_map.keys()
            }
            self._collection_name_by_uuid = dict(discover_map)
        else:
            self._collection_createable = {}
            self._collection_name_by_uuid = dict(discover_map)

        # Fallback: if discover list is empty, use create list for compatibility.
        source_map = discover_map
        if not source_map:
            source_map = self._get_collections_by_privilege("CREATE_ITEM")

        itemdefs = {}
        for uuid, name in source_map.items():
            itemdefs[name] = {"uuid": uuid}
        return itemdefs

    def _get_collections_by_privilege(self, privilege):
        start = 0
        length = 200
        collections = {}

        while True:
            payload = self._request(
                "GET",
                "/api/collection",
                params={"privilege": privilege, "start": start, "length": length},
            ) or {}

            results = payload.get("results") or []
            for collection in results:
                name = collection.get("name")
                uuid = collection.get("uuid")
                if name and uuid:
                    collections[uuid] = name

            batch_size = len(results)
            if batch_size == 0:
                break

            start += batch_size

            available = payload.get("available")
            if isinstance(available, int) and start >= available:
                break
            if batch_size < length:
                break

        return collections

    def _ensure_create_privilege_for_collection(self, collection_uuid, collection_name=None):
        if not collection_uuid:
            return

        collection_uuid = str(collection_uuid)

        if self._collection_createable:
            if not self._collection_createable.get(collection_uuid, False):
                resolved_collection_name = self._collection_name_by_uuid.get(
                    collection_uuid,
                    collection_name if collection_name else collection_uuid,
                )
                raise Exception(
                    "No CREATE_ITEM privilege for collection '%s'"
                    % resolved_collection_name
                )
            return

        # Fallback path if collection map is not preloaded.
        create_map = self._get_collections_by_privilege("CREATE_ITEM")
        if collection_uuid not in create_map:
            raise Exception("No CREATE_ITEM privilege for selected collection")

    def _forceUnlock(self, itemid, itemversion, *unused):
        version = self._resolve_item_version(itemversion)
        self._request("DELETE", "/api/item/%s/%s/lock" % (itemid, version))
        return None

    def _deleteItem(self, itemid, itemversion, *unused):
        version = self._resolve_item_version(itemversion)
        self._request("DELETE", "/api/item/%s/%s" % (itemid, version))
        return None

    def getItem(self, itemid, itemversion, select=""):
        item_json = self._get_item_json(itemid, itemversion, info="all")
        return self._item_json_to_propbag(item_json)

    def createNewItem(self, itemdefid):
        self._ensure_create_privilege_for_collection(itemdefid)

        file_uuid = self._create_file_area()
        seed_item = {
            "collection": {"uuid": itemdefid},
            "metadata": "<xml><item itemdefid='%s'/></xml>" % itemdefid,
            "attachments": [],
        }
        created = self._request(
            "POST",
            "/api/item",
            params={"draft": "true", "file": file_uuid},
            body=seed_item,
            include_response_meta=True,
        )

        if not isinstance(created, dict) or not created.get("uuid"):
            location = created.get("_location", "") if isinstance(created, dict) else ""
            created_itemid, created_itemversion = self._item_identity_from_location(location)
            if not (created_itemid and created_itemversion):
                raise Exception(
                    "REST create item returned no JSON body and no item location"
                )
            created = self._get_item_json(created_itemid, created_itemversion, info="all")

        itemid = created.get("uuid")
        itemversion = created.get("version")
        self._store_session(
            itemid,
            itemversion,
            file_uuid=file_uuid,
            lock_uuid="",
            created_draft=True,
            submitted=False,
        )

        dom = self._item_json_to_document(created, file_uuid=file_uuid)
        return NewItemClient(self, self.owner, dom, debug=self.debug)

    def newVersionItem(self, itemid, version, copyattachments=True):
        base_item = self._get_item_json(itemid, version, info="all")
        if copyattachments:
            file_uuid = self._copy_file_area(itemid, version)
        else:
            file_uuid = self._create_file_area()

        base_item["version"] = 0
        created = self._request(
            "POST",
            "/api/item",
            params={"draft": "true", "file": file_uuid},
            body=base_item,
            include_response_meta=True,
        )

        if not isinstance(created, dict) or not created.get("uuid"):
            location = created.get("_location", "") if isinstance(created, dict) else ""
            created_itemid, created_itemversion = self._item_identity_from_location(location)
            if not (created_itemid and created_itemversion):
                raise Exception(
                    "REST create new version returned no JSON body and no item location"
                )
            created = self._get_item_json(created_itemid, created_itemversion, info="all")

        new_itemid = created.get("uuid")
        new_itemversion = created.get("version")
        self._store_session(
            new_itemid,
            new_itemversion,
            file_uuid=file_uuid,
            lock_uuid="",
            created_draft=True,
            submitted=False,
        )

        dom = self._item_json_to_document(created, file_uuid=file_uuid)
        return NewItemClient(
            self,
            self.owner,
            dom,
            debug=self.debug,
        )

    def editItem(self, itemid, version, copyattachments):
        lock = self._request("POST", "/api/item/%s/%s/lock" % (itemid, version)) or {}
        lock_uuid = lock.get("uuid", "")

        copy_attachments = str(copyattachments).lower() == "true" or copyattachments is True
        if copy_attachments:
            file_uuid = self._copy_file_area(itemid, version)
        else:
            file_uuid = self._create_file_area()

        item_json = self._get_item_json(itemid, version, info="all")
        self._store_session(
            item_json.get("uuid"),
            item_json.get("version"),
            file_uuid=file_uuid,
            lock_uuid=lock_uuid,
            created_draft=False,
            submitted=False,
        )
        dom = self._item_json_to_document(item_json, file_uuid=file_uuid)
        return NewItemClient(
            self,
            self.owner,
            dom,
            newversion=0,
            copyattachments=copy_attachments,
            debug=self.debug,
        )

    def search(
        self,
        offset=0,
        limit=10,
        select="*",
        itemdefs=None,
        where="",
        query="",
        onlyLive=True,
        orderType=0,
        reverseOrder=False,
    ):
        if itemdefs is None:
            itemdefs = []

        order_map = {
            0: "modified",
            1: "name",
            2: "rating",
            3: "relevance",
        }
        params = {
            "start": offset,
            "length": limit,
            "q": query or "",
            "order": order_map.get(orderType, "modified"),
            "reverse": "true" if reverseOrder else "false",
            "showall": "false" if onlyLive else "true",
            "info": "basic,metadata,detail,attachment",
        }
        if itemdefs:
            params["collections"] = ",".join(itemdefs)
        if where:
            params["where"] = where

        search_json = self._request("GET", "/api/search", params=params) or {}

        doc = Document()
        root = doc.createElement("xml")
        doc.appendChild(root)

        available = doc.createElement("available")
        available.appendChild(doc.createTextNode(str(search_json.get("available", 0))))
        root.appendChild(available)

        for result in search_json.get("results", []):
            result_node = doc.createElement("result")
            result_xml = doc.createElement("xml")
            result_item = doc.createElement("item")
            if result.get("uuid"):
                result_item.setAttribute("id", str(result.get("uuid")))
            if result.get("version") is not None:
                result_item.setAttribute("version", str(result.get("version")))
            result_xml.appendChild(result_item)
            result_node.appendChild(result_xml)
            root.appendChild(result_node)

        return PropBagEx(root)

    def setOwner(self, itemid, itemversion, ownerid):
        item_json = self._get_item_json(itemid, itemversion, info="all")
        item_json["owner"] = {"id": ownerid}
        self._put_item_json(itemid, itemversion, item_json)
        return None

    def addSharedOwner(self, itemid, itemversion, ownerid):
        item_json = self._get_item_json(itemid, itemversion, info="all")
        collaborators = item_json.get("collaborators") or []

        existing_ids = set()
        for collaborator in collaborators:
            cid = collaborator.get("id")
            if cid:
                existing_ids.add(cid)

        if ownerid not in existing_ids:
            collaborators.append({"id": ownerid})
            item_json["collaborators"] = collaborators
            self._put_item_json(itemid, itemversion, item_json)
        return None

    def removeSharedOwner(self, itemid, itemversion, ownerid):
        item_json = self._get_item_json(itemid, itemversion, info="all")
        collaborators = item_json.get("collaborators") or []
        filtered = [c for c in collaborators if c.get("id") != ownerid]

        if len(filtered) != len(collaborators):
            item_json["collaborators"] = filtered
            self._put_item_json(itemid, itemversion, item_json)
        return None

    def getUser(self, userId):
        user_json = self._request("GET", "/api/usermanagement/local/user/%s" % userId)

        doc = Document()
        root = doc.createElement("user")
        doc.appendChild(root)

        mappings = {
            "id": user_json.get("id"),
            "username": user_json.get("username"),
            "firstName": user_json.get("firstName"),
            "lastName": user_json.get("lastName"),
            "emailAddress": user_json.get("emailAddress"),
        }
        for key, value in mappings.items():
            if value is not None:
                node = doc.createElement(key)
                node.appendChild(doc.createTextNode(str(value)))
                root.appendChild(node)

        return PropBagEx(root)

    def searchUsersByGroup(self, groupUuid, searchString):
        params = {}
        if groupUuid:
            params["group"] = groupUuid
        if searchString:
            params["q"] = searchString

        user_search = self._request("GET", "/api/usermanagement/local/user", params=params) or {}

        doc = Document()
        root = doc.createElement("users")
        doc.appendChild(root)

        for user_json in user_search.get("results", []):
            user_node = doc.createElement("user")
            for key in ("id", "uuid", "username", "firstName", "lastName", "emailAddress"):
                value = user_json.get(key)
                if value is not None:
                    node_name = "uuid" if key == "id" else key
                    node = doc.createElement(node_name)
                    node.appendChild(doc.createTextNode(str(value)))
                    user_node.appendChild(node)
            root.appendChild(user_node)

        return PropBagEx(root)
