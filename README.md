# EmailChronicle

> **Public preview downloads:** This repository and its GitHub release assets are public. Anyone can download the installer directly, without a website access code. The installer is unsigned and clean-laptop acceptance is pending. See [privacy review](docs/PUBLIC-REPOSITORY-PRIVACY.md) for exposure checks and their limits.

An offline Windows desktop application for reconstructing email timelines from local evidence. This first working slice supports **EML only**. It uses Python 3.12+, PySide6 and SQLite, with no cloud services, external AI calls or telemetry.

## Install without Python (Windows x64)

**Current local private preview: 0.1.3.** Users need only the setup EXE. It installs
Python/Qt/SQLite, notices, the matching source ZIP and a quick-start guide
automatically. No extra downloads, developer tools, Office, mail client or test
certificate are required for the application's core workflow. Source inspection
uses an inert built-in EML/hex viewer. This preview remains unsigned; clean-machine
acceptance and owner distribution decisions are still pending. See the local
release notes and test report before providing it to testers.


**Distribution review:** 0.1.0 is an unsigned preview with incomplete third-party
notices. Do not redistribute it as a reviewed commercial package. The 0.1.1
development build corrects notice/source packaging and prepares trusted signing;
it has not been published as a signed release. Publisher identity, an actual
signing credential and the application's license choice are still needed. See
[distribution status](docs/DISTRIBUTION.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

Download `EmailChronicle-Setup-0.1.0-x64.exe` from [GitHub Releases](https://github.com/MaximDascalasu/emailchronicle/releases/latest), run it and follow the setup wizard. Python and Qt are bundled; the installed app works offline. Installation is per user and does not require administrator rights. Start EmailChronicle from the Start menu; setup also offers an optional desktop shortcut. Supported target: Windows 10/11 x64.

This preview installer is unsigned, so Windows may display an unknown-publisher or SmartScreen warning. Verify that the download comes from this repository; code signing is a future distribution improvement. `SHA256SUMS.txt` on the release contains the installer checksum. Verify a download with `Get-FileHash .\EmailChronicle-Setup-0.1.0-x64.exe -Algorithm SHA256`.

Updates use the same installation directory and app ID. Run the newer setup to replace the program. Uninstall through Windows Settings; investigations and evidence in `%LOCALAPPDATA%\EmailChronicle` are retained. Keep evidence storage separate from the program installation folder. This version does not auto-download updates.

## Build the installer

On Windows x64 with Python 3.12 and [Inno Setup 6](https://jrsoftware.org/isdl.php) installed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,build]"
powershell -NoProfile -File scripts\build-windows.ps1
```

The build runs pytest, uses PyInstaller to bundle the app, runs an isolated executable smoke test (Qt, SQLite, EML parsing and source integrity), then compiles the setup EXE and checksum into `installer-output`. Use `-Iscc "C:\path\to\ISCC.exe"` for a custom compiler path. Third-party license files and synthetic samples are included in the app bundle.

GitHub Actions builds unsigned review artifacts via **Actions → Build Windows installer → Run workflow**. The output includes a third-party source archive, license notices, file inventory, signing status and checksums. Tag builds now require a configured signing identity, verified signatures and successful installation tests before publishing. The tag must match `pyproject.toml`; do not push a new release tag before completing [distribution setup](docs/DISTRIBUTION.md).

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
6. Select a row to inspect its cleaned text, original date text, parsing origin, source paths, locator and SHA-256. **Open source copy** verifies the hash and opens the preserved EML using the built-in read-only source viewer.
7. Search subject/content, filter sender, or enter ISO dates to filter UTC calendar days. Undated messages remain visible for review. Export CSV exports the currently visible rows with provenance and flags.
8. In the 0.1.1 development build, use **Help → How to use EmailChronicle** for an in-app explanation and **Help → Third-party licenses** to inspect the bundled notices.

## How it works

The desktop workspace includes an investigation sidebar, visible-message and
review summary cards, a resizable timeline beside an evidence inspector, and
separate Message and Provenance & review tabs. Use **Needs review only** to focus
on parsing warnings and duplicate hints. Counts reflect the current filters;
**Reset** clears all filters. Selecting a message keeps its provenance available
alongside its cleaned content. The source button checks integrity before opening.

A five-step guide across the top shows the path: **Create case → Import EML →
Read timeline → Check sources → Export CSV**. Click a step to perform its action
or focus the relevant panel. Contextual instructions explain the next action;
steps become available when a case and evidence exist. Highlighting is guidance,
not a claim that a message has been manually reviewed or authenticated.

Keyboard shortcuts: **Ctrl+N** creates an investigation, **Ctrl+O** imports EML,
**Ctrl+F** focuses search, and **Ctrl+E** exports CSV. Hover over truncated timeline
cells to read their full values. Resize the divider or column headers to suit
your screen. Review labels are informational; this version does not record a
manual reviewed/resolved status.

Create a case, select EML evidence and import it. The importer reads each original
without changing it, calculates its SHA-256 fingerprint, preserves a copy, then
parses the email headers and body. Recognizable forwarded headers become separate
message assertions linked to that same source. Original metadata and quoted-text
assertions are stored separately in SQLite.

The timeline converts known dates to UTC and sorts oldest first. Unknown times
remain undated and flagged. Exact file copies are skipped; likely duplicate
messages are marked for review rather than merged. Selecting a row shows its
content and provenance. Opening its source verifies the preserved file's hash
before displaying it in the built-in read-only EML/hex viewer. CSV export includes the visible
rows, review flags and source hash. Everything lives in the chosen local data
directory; there are no cloud or AI calls from the installed app.

The current app supports EML, CSV, PDF reports, Excel workbooks and graphs. It does not yet import MSG/PDF/DOCX/ZIP,
encrypt the workspace, or provide a tamper-proof audit
log. See the [prioritized roadmap](docs/ROADMAP.md).

## Reports and graphs

Choose **Export → Report bundle**, confirm the visible-message scope and select a
folder outside the evidence workspace. A uniquely named output folder contains:

- `investigation.pdf`: case details, active filters, warnings, charts, complete
  message content and provenance, with page numbers.
- `investigation.xlsx`: Overview, Messages, Evidence, Review, Communications and
  Audit sheets with frozen headers, filters and literal evidence strings rather
  than formulas. Long message bodies are split into numbered columns.
- Timeline, Gantt-style event lanes and directed communication graphs in **PNG,
  SVG and PDF**, paginated to include all occurrences.
- `export-data.json` with complete supporting data, and `SHA256SUMS.json` with
  generated-file hashes.

Graphs count every visible occurrence, including likely duplicates. Quoted and
original communication assertions remain separate. Missing/unparseable parties
receive no invented nodes. Undated messages stay off the time axis. Gantt-style
lanes show point events, never inferred durations. Abbreviated graph labels have
full values in the workbook and JSON. Reports are unsigned and certify no conclusions.

The Evidence sheet includes sources for visible messages. **Audit covers the whole
investigation**, potentially revealing information beyond current filters. Review
before sharing: the bundle includes complete content and local source paths.
The export audit event is recorded after success, so the exported audit snapshot
precedes its own export event. Failures leave a clearly marked partial folder.
Export runs on the UI thread and is intended for small collections. Excel row/cell
limits cause an explicit failure rather than silent evidence truncation.

## Evidence model and limits

Original input files are read only and never modified by the importer. Each imported file receives a separate managed byte-for-byte copy, SHA-256 hash, original path and import time. Opening a source uses the preserved copy, so the source remains available if the input is moved. The built-in viewer is read only; subsequent opening checks detect external changes to preserved copies. Back up the entire data directory together; stored copy paths are absolute in this release.

`investigations` groups separate collections; `sources` records original evidence; `messages` stores original metadata or quoted-text assertions with source IDs and body-line locators; `audit` records creation, imports, skipped duplicate files, UI import failures, source opening attempts, integrity failures and CSV exports. SQLite foreign keys and transactions enforce relationships. The audit trail is basic and locally editable, not a tamper-proof chain of custody. Database encryption, access control and cryptographic audit signing are outside this slice.

The parser prefers plain text and converts HTML to inert text without loading remote resources. The preserved EML retains the original content and attachments. Message rows separate recognized forwarded sections from the enclosing message body. English contiguous `From`, `Date`/`Sent`, `To`, `Cc` and `Subject` headers are recognized heuristically, including `>` quote prefixes. Quoted messages always carry `quoted_headers_unverified`; header-like prose may be misidentified. Localized headers, wrapped forwarded headers, `On … wrote` forms and attached EML messages are not reconstructed in this version. Dates that cannot be interpreted conservatively are flagged for review. Neither missing dates nor sender information is invented.

Exact file duplicates are skipped per investigation and logged with their submitted path. Likely message duplicates are flagged by matching normalized content plus available metadata, or matching Message-ID, within an investigation. This is a review hint, not proof; messages are never silently merged. CSV cells that could be spreadsheet formulas receive an apostrophe prefix; the evidence and stored message text remain unchanged.

## Architecture and next increments

- `parser.py`: byte-to-message extraction independent of storage and UI.
- `store.py`: SQLite schema, managed evidence copies, timeline queries, hashes and audit events.
- `app.py`: minimal PySide6 desktop workspace, source opening and CSV export.
- `tests`: synthetic parser, persistence, integrity, duplication, ordering and UI smoke tests.

Next increments should introduce format adapters that return the same message model and preserve format-specific provenance. MSG, PDF, DOCX and safe ZIP import, native Excel export, richer review/edit workflows, large-file background ingestion and optional Gmail/Outlook connectors are deliberately deferred until after this slice. Import currently runs on the UI thread and is intended for small evidence batches. No credentials or real evidence are included in this repository.


## Explainable search without AI

Choose **Exact**, **Expanded**, or **Approximate** above the timeline. All query
terms are required (AND); put multiword phrases in double quotes. Matching is
case-insensitive and uses whole-word boundaries across subject, body, sender,
recipients and Message-ID. Sender and UTC date filters still apply. This replaces
the original keyword substring filter in the desktop interface. Search operators
such as OR/NOT and automatic language understanding are not implemented.

Open **Synonyms & aliases…** to define groups for the selected investigation:

```text
+ Payment | payment | remittance
+ Project | Phoenix | PHX
- Ambiguous terms | payment | settlement
```

`+` explicitly enables a group; `-` excludes it. No default dictionaries are
silently enabled. In Expanded mode, searching `Phoenix payment` also finds
`PHX remittance` with these groups enabled. Quote a multiword dictionary term to
expand it as a unit. Expansions are direct, bidirectional within a selected group,
and not recursively chained across groups. Save versions and complete before/after
definitions are recorded in the local audit trail. They never modify email evidence.

Approximate mode also uses selected synonym groups and offers spelling tolerance
for the original query terms: alphabetic words of at least five characters,
length difference at most one, SequenceMatcher similarity at least 0.84. It does
not infer equivalence of meaning. Exact and synonym matches take precedence over
spelling suggestions for each term. Dates, numbers and short words are not fuzzed.

Each selected result explains its matches; matching words are highlighted in the
message inspector. **Rank by relevance** is optional: exact terms score 100,
synonyms 60, approximate suggestions 25, taking the best match per required term.
Ties retain timeline order. Default results remain chronological, with unknown
dates last. Reset clears the query and returns to Exact chronological mode.

CSV includes search settings, dictionary snapshot, score and match explanations.
Report bundles preserve those settings and explanations as well. Scores indicate
search matching strength, never evidential importance or credibility. Search is
performed locally over the selected investigation and is designed for small
collections; a persistent full-text index is a future performance improvement.
