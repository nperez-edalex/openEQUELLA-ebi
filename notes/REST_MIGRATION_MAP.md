# REST Migration Map (EBI)

This document tracks the SOAP methods currently used by EBI and their REST migration target.

## Scope

Used call surface extracted from `Engine.py` and `RowProcessor.py`:

- TLEClient methods:
  - `_enumerateItemDefs`
  - `search`
  - `getItem`
  - `createNewItem`
  - `editItem`
  - `newVersionItem`
  - `setOwner`
  - `addSharedOwner`
  - `removeSharedOwner`
  - `getUser`
  - `searchUsersByGroup`
  - `getFile`
  - `getText`
  - `logout`
  - `_deleteItem`
  - `_forceUnlock`
- NewItemClient methods:
  - `attachFile`
  - `attachIMS`
  - `attachSCORM`
  - `attachResource`
  - `addUrl`
  - `addStartPage`
  - `deleteAttachments`
  - `submit`
  - `getXml`

## Incremental Plan

1. Compatibility entry point
- Done: created `source/equellaclient.py` facade and switched imports to it.

2. Transport switch in facade
- Add transport selector (`soap` default, `rest` opt-in).
- Keep public class names stable (`TLEClient`, `NewItemClient`, `PropBagEx`, `XPath`).

3. REST TLEClient foundation
- Done: constructor/session/auth scaffold implemented.
- Done: common REST request helper implemented.
- Done: preserves `institutionUrl` and broad exception style used by UI/engine.

4. Read-only operations first
- Done (initial implementation):
  - `_enumerateItemDefs`
  - `search`
  - `getItem`
  - `getUser`
  - `searchUsersByGroup`
  - `getText`
  - `getFile`

5. Mutating operations
- Done (initial implementation): `createNewItem`
- Done (initial implementation): `editItem`
- Done (initial implementation): `newVersionItem`
- Done (initial implementation): `submit` (save)
- Done (initial implementation): owner/collaborator updates
- Done (initial implementation): `_deleteItem`, `_forceUnlock`
- Done (initial implementation): attachment upload for file/url/linked-resource flows
- Done (initial implementation): unzip behavior via local ZIP expansion + file area upload
- Done (initial implementation): IMS/SCORM/ZIP attachment type mapping in REST XML<->JSON conversion
- Remaining: validate IMS/SCORM package semantics against live openEQUELLA instance

6. Remove SOAP dependency
- Switch default transport to REST.
- Keep SOAP fallback for one release window if needed.

## Validation Checklist

- Can connect and list contributable collections.
- Can find existing items with source identifier.
- Can create new item and submit.
- Can edit existing item and submit.
- Can create new version.
- Can upload attachments (regular, zip/IMS/SCORM where supported).
- Can set owner and collaborators.
- Export mode can download item files.
- Issue #31 save/exit flow remains fixed.
