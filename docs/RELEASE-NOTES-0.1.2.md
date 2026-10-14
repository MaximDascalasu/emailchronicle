# EmailChronicle 0.1.2 — private unsigned preview

## Changes

- Dispose native windows, deferred deletion events and signal-reference cycles
  while QApplication is still alive. This addresses the reproducible Qt teardown
  crash; no forced process exit or security-control changes are used.
- Add a regression test for native window destruction and an installed-preview
  acceptance harness with repeated launches and normal event-loop shutdown.
- Package current explainable exact/synonym/approximate search, case-specific
  dictionary auditing and provenance-aware CSV/PDF/Excel/graph exports.
- Shorten installed third-party notice paths, retaining complete notice bytes,
  upstream path mappings and exact-version source archives. This fixes setup
  rollback caused by deeply nested upstream notice paths.
- Explicitly label unsigned preview setup and record build verification status.

## Requirements and limits

Installer targets Windows 10 build 17763 or newer, Windows 11, x64-compatible
systems. Native x64 is the tested architecture; ARM64 compatibility is not verified.
Python, PySide6/Qt and SQLite are bundled; no separate Python or Office install is
required. Viewing EML sources requires a configured external EML viewer.

Local automated testing is not a clean-machine certification. See TEST-REPORT.md
for the exact environment and completed checks. Internet is not required for
installed evidence processing; build/source acquisition requires network access.

EML import only. MSG/PDF/DOCX/ZIP and MBOX import, direct mailbox connections,
portable investigation transfer and encryption are not implemented. Audit storage
is not tamper-proof. Quoted headers, dates and duplicate hints require review.

## Distribution status

UNSIGNED. No publicly trusted publisher identity or Authenticode timestamp is
claimed. Do not disable security controls to run a blocked preview. App licensing,
legal publisher identity and Microsoft runtime redistribution review await owner
confirmation. This is not approved for public/commercial distribution.

Supply the installer together with matching third-party notices and the source
companion, with the same recipient access. Keep the actual installer in the access
plugin's private storage outside the web root, not the theme or Media Library.
Nothing in this release process uploads or publishes the files.
