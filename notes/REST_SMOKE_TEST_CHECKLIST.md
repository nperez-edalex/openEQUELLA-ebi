# REST Smoke Test Checklist

Use this checklist to validate REST transport behavior on a test institution.

## Prerequisites

- Branch contains REST migration changes.
- Test openEQUELLA instance with a collection you can write to.
- A small CSV and attachments set prepared.
- Set environment variable before running EBI:
  - `EBI_API_TRANSPORT=rest`

Windows helper:
- `./scripts/run-rest-mode.ps1`

Optional auth:
- `EBI_REST_ACCESS_TOKEN` or `EBI_REST_ADMIN_TOKEN`

If credential login returns 404 on `j_spring_security_check`/`j_security_check`, use token auth.

Non-GUI smoke script (read-path):
- `python scripts/rest-smoke.py`
- Required env vars:
  - `EBI_TEST_INSTITUTION_URL`
  - `EBI_TEST_USERNAME`
  - `EBI_TEST_PASSWORD`

## Test Cases

1. Connection and collections
- Open EBI and fetch collections.
- Expected: collection list loads successfully.

2. Basic create
- Import one new row with metadata only.
- Expected: item created; source identifier receipt generated.

3. Basic edit
- Re-run same source identifier with metadata changes.
- Expected: item updated.

4. New version
- Enable new-version mode.
- Import row for existing source identifier.
- Expected: next version created.

5. Standard file attachment
- Import with file attachment and display name.
- Expected: file appears as attachment and opens.

6. URL attachment
- Import with URL/hyperlink name.
- Expected: URL attachment created.

7. Linked resource attachment
- Import linked-resource row.
- Expected: linked-resource attachment created.

8. Owner and collaborators
- Import owner and collaborator columns.
- Expected: owner/collaborators updated.

9. UNZIP command
- Import ZIP with `UNZIP` command.
- Expected: zip plus extracted attachments appear.

10. IMS package
- Import package with `IMS` command.
- Expected: package attachment and package metadata are preserved.

11. SCORM package
- Import package with `SCORM` command.
- Expected: scorm attachment preserved and launch behavior valid.

12. Export sanity
- Export rows including normal file, IMS/SCORM, and unzip-derived attachments.
- Expected: files download and CSV output remains consistent.

## Known Risks To Watch

- Item save conflict when edit lock is stale.
- Attachment type conversions for package-related types.
- REST endpoint differences across openEQUELLA versions.

## Capture For Debugging

- EBI log file from `logs/`.
- Any response error payload shown in error dialogs.
- The exact row and command options that failed.
