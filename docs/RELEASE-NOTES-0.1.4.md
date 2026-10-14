# EmailChronicle 0.1.4 — evaluation preview

This release is unsigned. It is available for evaluation; trusted signing,
independent clean-machine acceptance and the remaining runtime redistribution
review are still pending. It is not labelled a verified production release.

## Changes

- Bound repetitive-message search explanations and highlights without changing
  preserved evidence or AND-query membership; account for UTF-16 Unicode offsets.
- Apply MIT to EmailChronicle source and include LICENSE in the installed bundle.
- Access plugin 0.2.1 supports a configured installer version and verifies
  acceptance, private storage and SHA-256 on every download. Changing acceptance
  disables an existing configured file immediately.
- Require nonlocal HTTPS for access requests. Public GitHub asset sync needs no
  stored token; private-asset credentials remain server-side.
- Align WordPress theme 1.2.17, plugin instructions and public-download wording.

## Privacy and download access

Source and GitHub release assets are public. GitHub downloads require no access
code. WordPress code entry controls only the site's download endpoint. Request
records, page passwords, evidence, databases, signing keys and server configuration
are not release assets. Samples and screenshots use synthetic evidence.

The author's name, GitHub identity, public support address and historical commit
metadata remain public. No history rewrite or deletion of existing downloads was
performed. Pattern checks and static review do not guarantee absence of every risk.

## Validation

- 47 application tests passed before packaging.
- Bundled executable smoke checks passed: Qt, SQLite, EML, hashes, expanded search,
  PDF/Excel/graph and CSV export, source viewer, event-loop exit and native disposal.
- Developer-host install, normal launch/shutdown, two installed-runtime smoke runs,
  bundled-source verification and uninstall preserving workspace data passed for
  both local candidates. The GitHub Windows runner also passed installation,
  installed-runtime smoke tests and uninstall preservation before publication.
- Standalone plugin tests cover missing acceptance/hash, changed bytes, wrong or
  invalid versions and acceptance withdrawal. Local WordPress tests cover code
  validation, cookie rotation, expiring grants and request/download presentation.
- Current-source security review found no validated exploitable vulnerability;
  supporting historical documents and live hosting were not fully audited.
- History exposure check covered 114 Git blobs: no checked credential-pattern,
  active local access-code or sensitive configuration/data filename matches.
  GitHub reported zero open secret alerts; push protection is enabled.

Publishing a theme release does not install it on Hostinger or transfer WordPress
database settings. Production access-code delivery requires separate deployment.
