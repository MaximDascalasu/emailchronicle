# EmailChronicle 0.1.7 release validation

Validated locally on 21 October 2026. Version advanced from 0.1.6 to 0.1.7.
Access plugin advanced from 0.2.4 to 0.2.5.

- 58 application tests passed.
- Source and frozen executable smoke tests passed, including mixed EML/MSG import,
  MSG duplicate checks, original bytes and hashes, decoded MSG source display,
  CSV/PDF/Excel/graph exports, search and shutdown.
- Installer built with bundled Python, Qt, MIT-licensed MSG parser, notices and
  third-party source companion. No Outlook installation is required.
- Developer-host installation, runtime inventory verification, normal launch and
  shutdown, two installed-runtime smoke checks, and uninstall preservation passed.
- 12 standalone WordPress release-gate assertions passed; changed PHP files passed
  syntax checks. Live WordPress integration tests and deployment were not run.
- Dependency consistency and Git whitespace checks passed.

Installer: `EmailChronicle-Setup-0.1.7-x64.exe`

SHA-256: `4a0851dc6adecc56dc6adb6bde1881081126cc978c9bb279b7f10960a172281e`

Artifacts are in `installer-output/0.1.7/`. The website plugin pins this installer
checksum. Its ZIP contains the updated plugin; WordPress template changes are
also supplied in the WordPress update ZIP. No hosting settings were changed.

This installer is unsigned. Independent clean-machine acceptance, trusted signing
and runtime redistribution review remain pending. RTF-only MSG bodies remain
flagged for review. No GitHub release or website deployment was performed.

Changes remain on `codex/add-msg-import`, uncommitted, with earlier local edits
preserved. No pull request or merge was created.
