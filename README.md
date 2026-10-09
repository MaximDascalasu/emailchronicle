# EmailChronicle

An offline Windows desktop application for reconstructing email timelines from local evidence. This first working slice supports **EML only**. It uses Python 3.12+, PySide6 and SQLite, with no cloud services, external AI calls or telemetry.

## Windows setup

Install Python 3.12 or newer from python.org, including the Python launcher. In PowerShell:

```powershell
git clone git@github.com:MaximDascalasu/emailchronicle.git
cd emailchronicle
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m emailchronicle.app
```

No PowerShell activation-policy change is required. If using a newer Python, replace `-3.12` with that version. Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Optional explicit storage location:

```powershell
.\.venv\Scripts\python.exe -m emailchronicle.app --data-dir C:\EmailChronicleData
```

The default storage directory is `%LOCALAPPDATA%\EmailChronicle`. Choose a local directory outside OneDrive or other synchronized folders to keep evidence local. The application itself makes no network requests; operating-system synchronization and the external EML viewer are outside its control.

## Try the synthetic evidence

1. Create an investigation, then import the five EML files in `samples` in any order.
2. The timeline sorts known timestamps in UTC: the initial message and quoted copy at 10:30, then the follow-up at 11:00 on 7 July 2026.
3. The initial message, its second export and quoted copy are marked as likely duplicates. All occurrences retain their own provenance.
4. The undated note and unknown-timezone message appear last with review flags. Their times are not guessed.
5. Import the same file again to see exact-file deduplication. Create a second investigation to see separate evidence collections.
6. Select a row to inspect its cleaned text, original date text, parsing origin, source paths, locator and SHA-256. **Open source copy** verifies the hash and opens the preserved EML using the Windows file association.
7. Search subject/content, filter sender, or enter ISO dates to filter UTC calendar days. Undated messages remain visible for review. Export CSV exports the currently visible rows with provenance and flags.

## Evidence model and limits

Original input files are read only and never modified by the importer. Each imported file receives a separate managed byte-for-byte copy, SHA-256 hash, original path and import time. Opening a source uses the preserved copy, so the source remains available if the input is moved. The external viewer can potentially modify that copy; subsequent opening checks detect hash changes. Back up the entire data directory together; stored copy paths are absolute in this release.

`investigations` groups separate collections; `sources` records original evidence; `messages` stores original metadata or quoted-text assertions with source IDs and body-line locators; `audit` records creation, imports, skipped duplicate files, UI import failures, source opening attempts, integrity failures and CSV exports. SQLite foreign keys and transactions enforce relationships. The audit trail is basic and locally editable, not a tamper-proof chain of custody. Database encryption, access control and cryptographic audit signing are outside this slice.

The parser prefers plain text and converts HTML to inert text without loading remote resources. The preserved EML retains the original content and attachments. Message rows separate recognized forwarded sections from the enclosing message body. English contiguous `From`, `Date`/`Sent`, `To`, `Cc` and `Subject` headers are recognized heuristically, including `>` quote prefixes. Quoted messages always carry `quoted_headers_unverified`; header-like prose may be misidentified. Localized headers, wrapped forwarded headers, `On … wrote` forms and attached EML messages are not reconstructed in this version. Dates that cannot be interpreted conservatively are flagged for review. Neither missing dates nor sender information is invented.

Exact file duplicates are skipped per investigation and logged with their submitted path. Likely message duplicates are flagged by matching normalized content plus available metadata, or matching Message-ID, within an investigation. This is a review hint, not proof; messages are never silently merged. CSV cells that could be spreadsheet formulas receive an apostrophe prefix; the evidence and stored message text remain unchanged.

## Architecture and next increments

- `parser.py`: byte-to-message extraction independent of storage and UI.
- `store.py`: SQLite schema, managed evidence copies, timeline queries, hashes and audit events.
- `app.py`: minimal PySide6 desktop workspace, source opening and CSV export.
- `tests`: synthetic parser, persistence, integrity, duplication, ordering and UI smoke tests.

Next increments should introduce format adapters that return the same message model and preserve format-specific provenance. MSG, PDF, DOCX and safe ZIP import, native Excel export, richer review/edit workflows, large-file background ingestion and optional Gmail/Outlook connectors are deliberately deferred until after this slice. Import currently runs on the UI thread and is intended for small evidence batches. No credentials or real evidence are included in this repository.
