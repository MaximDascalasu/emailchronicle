# Public-repository privacy review — 2026-10-14

## Findings and protections

- Repository visibility verified public. The v0.1.3 installer is directly downloadable from GitHub; a website access code cannot restrict that public URL. Release description updated to make this explicit. Application source code is intentionally public.
- Reviewed 107 historical Git blobs across fetched branches/tags. No matches for the checked GitHub/API credential formats, private-key headers, credential-bearing URLs or current local preview access code. No private configuration, certificate private-key files or case database files appeared in the Git history file inventory.
- The five checked EML samples use synthetic example.test identities. No real investigation evidence was identified in the tracked files.
- Checked all 32 Actions runs available at the start of review: 64 log files, no checked secret-pattern or exact active-Git-credential/access-code matches.
- Enumerated all 11 available Actions artifact ZIP inventories and checked 41 text/JSON metadata files by range download. No sensitive evidence/database/key filenames or checked secret matches. Installer and vendor-source binaries were not exhaustively reverse-engineered.
- Checked the release plugin ZIP, source-companion notices/metadata and public release text assets. No checked secret matches. Vendor source tarballs are the upstream hash-pinned Qt/PySide archives; this review did not rescan every upstream source file.
- Enabled GitHub secret scanning and secret-scanning push protection. GitHub reported no open secret alerts at review time. This is a snapshot, not proof of absence of every possible secret.
- Expanded .gitignore to keep private configuration, case databases, email evidence, signing keys, logs and installer binaries out of normal Git staging. The existing five synthetic EML samples remain allowed. Ignore rules do not stop explicit forced staging or protect files already tracked.
- Set this checkout's future commit email to GitHub's no-reply address. The global Git identity was not changed.

## Personal information that remains public

The owner's publisher name, GitHub handle, support Gmail address and earlier commit author email are public. These are identifiers/contact details, not authentication credentials. The support address was previously supplied for the product. Changing future commit settings does not remove old metadata, forks, clones or cached copies. No destructive history rewrite was performed.

The real local preview access code and WordPress/GitHub/SMTP configuration remain outside this repository. Test strings such as synthetic-code-for-testing are deliberately non-production fixtures. No real email was sent during this review.

## Limits

This is a focused public-exposure review, not a complete application vulnerability audit or a guarantee of zero risk. Binary installers and third-party source archives were not fully reverse-engineered. GitHub alerts and pattern checks can miss unsupported secret formats. Later changes and uploads require their own checks.

The 0.1.3 installer remains unsigned; development-host Windows policy blocked its setup and clean-laptop acceptance remains pending. Public visibility does not resolve that issue or the pending application licence/runtime redistribution review. No Windows security controls were bypassed. The public repository grants visibility, not an automatically selected open-source licence.
