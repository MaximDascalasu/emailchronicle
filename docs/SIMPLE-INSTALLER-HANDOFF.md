# Simple user installation and publisher handoff

The user receives only `EmailChronicle-Setup-0.1.7-x64.exe`:

**Download → Run setup → Open EmailChronicle → Create investigation → Import EML or MSG**

Python, Qt, SQLite, runtime files, third-party notices, the corresponding source
ZIP and a quick-start guide are installed automatically. No manual prerequisites,
certificate installation, command line, Python environment or Office installation
is required for the core investigation/export workflow. The built-in source
viewer needs no Outlook, Thunderbird or other mail application.

Publisher-side release notes, checksums, test harness, inventories and standalone
source ZIP are administrative records. They are not additional user installation
steps. The same source ZIP is included in the setup and is available locally via
Help > Third-party licenses, so distributing the single EXE preserves that access.
Do not remove the embedded sources or notices when repackaging.

The installer performs no runtime download. It uses a per-user application folder
and creates a Start menu shortcut. Investigation data is in a separate LocalAppData
folder and is retained on uninstall. Viewing exported spreadsheets can use an
optional compatible viewer; creating exports does not require one.

Current preview remains unsigned. Before a general rollout, resolve clean-machine
acceptance, actual publisher identity, application licensing and runtime review.
Trusted Authenticode signing is the professional way to identify the publisher;
never ask users to trust a self-signed certificate or disable security controls.

The access website should present one main download button for the approved EXE.
Keep the file outside public web access and serve it through the existing access
plugin. Do not upload the installer to the theme or Media Library. Publication and
portal configuration are outside this local build task and have not been performed.
