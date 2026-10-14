# EmailChronicle 0.1.3 — one-installer private preview

## User setup

Download one `EmailChronicle-Setup-0.1.3-x64.exe`, run setup, then open the app
from the Start menu. Required runtimes, libraries, notices, source archive and
quick-start guide are installed automatically. No Python, Qt, Office, AI model,
mail client, test certificate or developer tools need to be installed separately.
There are no installation-time downloads. Installation is per user, with an
optional desktop shortcut. Uninstall keeps investigation data.

A compatible spreadsheet application is optional if users want to open exported
XLSX files; none is required to create them. The app works offline after install.

## Changes since 0.1.2

- Include the exact-version third-party source companion inside setup. It is
  installed as `_internal/third-party-notices/ThirdPartySources.zip` and is
  accessible through Help > Third-party licenses. The separate build ZIP is
  optional for publisher records; end users need only the installer.
- Add an inert, read-only source viewer for original EML text and byte hex.
  File integrity is checked before display. No HTML, links or attachments execute.
  Text is displayed as UTF-8 with replacement for undecodable bytes. Explicit
  preview limits are 2 MiB of text and 64 KiB of exact hex; preserved evidence
  remains complete and unchanged.
- Simplify setup: use the per-user install location automatically and remove the
  redundant Ready page. Include QUICK-START.txt without additional configuration.
- Verify installed application operation with developer Python/Qt paths removed
  from the test environment. Verify the installed source archive checksums.

## Preview status

UNSIGNED. No publicly trusted publisher or timestamp is claimed. Do not install
certificates or disable Windows security controls to make a blocked preview run.
Clean Windows machine acceptance, legal publisher identity, application licence
and redistribution review remain outstanding. This does not claim public release
approval. See TEST-REPORT.md for exact checks performed.

Distribution: private GitHub preview release. The website must serve a verified copy from private server storage after access-code validation, never from the theme or Media Library. Production downloads remain disabled until laptop acceptance. Publishing this preview does not resolve signing, licensing or redistribution review.
