# Distribution and signing status

## What is complete

The build bundles Python and a minimal Qt desktop runtime. It collects full
upstream licenses/notices and prepares an exact-version QtBase/PySide/Shiboken
source companion. SHA-256 checks verify the upstream source archives against
recorded publisher digests. A final bundle inventory blocks unreviewed Qt DLLs
and plugins. Original evidence is never included in build assets.

The application, setup and uninstaller can be signed using a certificate in the
builder's Windows CurrentUser Personal certificate store. Unsigned dependency
EXE/DLL/PYD files are also signed for distribution; valid existing upstream
signatures are preserved. The signing helper requires code-signing EKU, an
accessible private key, matching publisher identity, a valid trusted chain and
online revocation validation. It uses SHA-256 and an RFC3161 timestamp, then
verifies the result. It rejects self-signed certificates. Signing a binary does
not establish copyright ownership or replace a software license.

## What remains unresolved

- No suitable signing certificate was present during the local review. No
  certificate has been purchased, created or imported. No cloud signing account
  has been provisioned. The published 0.1.0 installer remains unsigned.
- The copyright owner must choose the license for EmailChronicle's own code and
  confirm the publisher's legal name. No MIT or other open-source grant has been
  applied without that choice.
- Confirm Microsoft runtime redistribution rights for the build toolchain
  before commercial distribution. Vendor-provided files and notices must retain
  their applicable terms; access to a wheel alone is not recorded proof of an
  independently purchased Microsoft entitlement.
- Inno Setup's authors request a commercial license purchase from commercial
  users; their FAQ states it is not strictly required. No purchase has been made.
- The new packaging controls address future builds. The 0.1.0 bundle included
  unused Qt plugins and incomplete notices. Do not redistribute that installer
  as a reviewed commercial package. Use the corrected source/notice build and
  complete these items before a new signed release.

This is an engineering distribution record, not a legal opinion or a guarantee
of compliance in every jurisdiction.

## Build previews

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test,build]"
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
```

Preview builds are explicitly recorded as unsigned in `signing-status.json`.
Never label a preview as signed. Build downloads require network access to
obtain sources and notices; the installed evidence app remains offline.

## Build a signed release after identity setup

Install Microsoft Windows SDK signing tools. Obtain a certificate issued to the
actual publisher from a trusted code-signing CA, with its private key protected
by the provider's required hardware or managed service. A hardware-backed
certificate exposed in the Windows certificate store works with this helper;
the signing provider may prompt for its PIN. Never put a private key or password
in Git, chat, build arguments or logs.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 `
  -RequireSigning `
  -CertificateThumbprint YOUR_PUBLIC_CERTIFICATE_THUMBPRINT `
  -Publisher "EXACT CERTIFICATE PUBLISHER NAME"
```

`-TimestampUrl` selects the CA-approved RFC3161 timestamp endpoint. A thumbprint
is a public identifier, not the private key. `-RequireSigning` fails before the
build if no certificate is configured. Checksums are generated after signing.

GitHub tag builds now require signing and will fail until a secure signing
identity is provisioned in the release build environment. Repository variables
alone do not install a certificate or key. A managed signing service needs its
own integration and identity verification; those are not yet configured. Manual
workflow runs produce reviewable unsigned artifacts with sources and notices,
but cannot publish a tagged release as signed. No new release tag should be
pushed until identity and licensing decisions are complete.
Record the chosen application license, matching publisher name, completed runtime
redistribution review and reviewer in `packaging/distribution-status.json`.
Signed release builds also refuse to proceed while that record is incomplete.

## Qt library replacement

Qt/PySide/Shiboken DLLs remain separate in `_internal`. Replace them with
ABI-compatible modified builds while the app is closed; the app does not enforce
signature/inventory checks on these libraries at runtime. Preserve a separate
copy of the installed program for testing modifications. Evidence hashes apply
to evidence files, not to library replacement. The source companion contains
upstream build scripts and documentation. Consult its LGPLv3/GPLv3 texts for
the full terms; the app places no additional restriction on LGPL debugging.

Primary references:

- https://www.qt.io/development/open-source-lgpl-obligations
- https://doc.qt.io/qt-6/qtvirtualkeyboard-index.html
- https://pyinstaller.org/en/stable/license.html
- https://jrsoftware.org/isorder.php
- https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
- https://jrsoftware.org/ishelp/topic_setup_signeduninstaller.htm
