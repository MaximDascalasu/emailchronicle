# Certificates and getting started

## What is ready

EmailChronicle runs locally without a certificate. Certificates authenticate the
publisher of downloaded Windows software; they do not encrypt investigations,
validate email authors, or certify forensic conclusions.

`scripts/create-test-certificate.ps1` creates or reuses a 90-day, RSA 3072,
SHA-256 code-signing certificate named **EmailChronicle LOCAL TEST ONLY** in
`Cert:\CurrentUser\My`. Its private key is nonexportable. It exports only a public
`.cer` and diagnostic metadata into ignored `.local-signing/`, signs a harmless
PowerShell probe, and checks that a changed probe is rejected. Windows can report
`NotSigned` rather than `HashMismatch` for the changed probe. An untrusted-chain
status on the original is expected. Neither probe is executed.

Run from the repository in PowerShell:

```powershell
./scripts/create-test-certificate.ps1
Get-Content .local-signing/test-certificate.json
```

The script does not install any trusted root or publisher. Do not install this
test certificate as a trusted root to bypass Windows warnings. It cannot be used
by the production release helper. No private certificate or password belongs in
GitHub, chat, or source control. The key stays on this Windows account/machine;
copying the public `.cer` does not copy signing capability.

## What you must supply for a trusted public release

1. Decide the legal publisher name, country, and individual/company status.
2. Obtain an identity-verified code-signing certificate from a public certificate
   authority, or enroll in Microsoft Artifact Signing if eligible. This normally
   involves identity checks and payment; a local script cannot issue public trust.
   Follow the provider's hardware-backed key or managed-signing process rather
   than generating an exportable production key here.
3. Choose the application's license and complete the runtime redistribution
   review recorded in `packaging/distribution-status.json`. Bundled dependency
   notices and source archives are prepared, but that is not legal certification.
4. Install Windows SDK SignTool and Inno Setup on the build machine. Supply the
   production certificate/provider access securely. The current helper supports
   a usable certificate in CurrentUser/My; managed signing services require a
   provider-specific CI integration before they work with this workflow.
5. Configure the reviewed publisher and certificate, build, verify, and then
   publish a new release. Hosted GitHub runners do not inherit this computer's
   certificate store. Repository variables alone cannot provision a private key.

For the current Windows certificate-store signing implementation:

```powershell
$env:EMAILCHRONICLE_PUBLISHER = 'Your verified certificate publisher name'
$env:EMAILCHRONICLE_SIGNING_THUMBPRINT = 'YOUR_40_HEX_CHARACTER_THUMBPRINT'
./scripts/build-windows.ps1 -Python .venv/Scripts/python.exe -RequireSigning
```

Complete the distribution status fields truthfully before running that command.
The build signs unsigned application binaries, preserves valid dependency
signatures, signs the setup and uninstaller, timestamps and verifies signatures,
and emits checksums, notices, a source companion, and an inventory. The same
publisher identity is used across these outputs. The issuing authority supplies
its certificate chain; the timestamp service supplies its timestamp certificate.
There is no need to create a web-server certificate for this offline application.
Even publicly trusted signing does not guarantee immediate SmartScreen reputation.

Official references:
- [Microsoft self-signed testing certificates](https://learn.microsoft.com/en-us/powershell/module/pki/new-selfsignedcertificate)
- [Artifact Signing setup and identity verification](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart)
- [Windows signing options and SmartScreen](https://learn.microsoft.com/en-us/windows/msix/package/sign-msix-package-guide)
- [SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool)

## Install and use the application

The existing GitHub v0.1.0 installer is an **unsigned preview**, predating the
0.1.1 licensing/package improvements. It is not a completed signed release.
Download from the private repository's Releases page while signed into GitHub,
run setup, and launch EmailChronicle from Start. No separate Python installation
is needed for the packaged application. Setup installs per user; uninstall keeps
investigation data. See README for development installation and build commands.

1. Create an investigation and give it a descriptive name.
2. Import EML or MSG files. Each investigation has its own evidence collection.
3. Read the timeline, ordered oldest to newest in UTC. Missing or uncertain dates
   are flagged; unknown dates appear last rather than receiving invented times.
4. Select a message to inspect content, provenance, and parsing warnings. Quoted
   or forwarded headers are marked separately from original email metadata.
5. Search by sender or keywords and apply date filters. Undated messages remain
   visible for review. Likely duplicates are flagged rather than silently merged;
   identical file hashes prevent repeated file imports within an investigation.
6. Use Open source to open the preserved EML copy after a hash check. External
   mail software controls its own behavior when opening that file.
7. Export the current timeline to CSV. CSV cells are escaped against spreadsheet
   formula execution; stored evidence content remains unchanged.

The application copies evidence without editing the originals, stores hashes,
provenance and a basic audit trail in local SQLite, and makes no cloud/AI calls.
Installed data lives under `%LOCALAPPDATA%\EmailChronicle`. Back up this entire
folder together; managed evidence paths currently require care when moving to a
different location. SQLite data is not encrypted and the audit trail is not
tamper-proof. Protect the Windows account and storage appropriately.

PDF, DOCX and ZIP import are not implemented in this first
slice. The next recommended improvement is a manual-review queue that preserves
raw parsed values alongside investigator corrections and records those changes.
