# Dual-access preview validation — 2026-10-14

- App suite: 46 passed (this change); earlier 0.1.3 independent repeat runs: 10 x 46, all exit zero.
- PHP syntax checks: theme and plugin passed.
- Local HTTP page: both request form and code entry visible without authentication.
- Synthetic request validation: invalid email, acknowledgement and honeypot denied; valid request stored pending and administrator notified through local Mailpit. Confirmation wording assertion updated after text change. Synthetic requests removed afterwards; no real email sent.
- Code checks: absent/wrong denied, correct accepted, rotation revokes old cookie, empty code fails closed.
- Private-download handler: synthetic file returned byte-for-byte with authorized cookie. Real installer remains disabled in persistent configuration.
- Existing manual-grant regression: pending/wrong/expired/revoked tokens denied; renewal invalidates prior token; rate limit checks passed.
- Native WordPress code submission tested over HTTP: wrong code stays locked, correct code unlocks the download state.
- GitHub administrator sync tested locally against private release asset 640260356; downloaded copy matched SHA-256. The credential was supplied only to the test process, not saved in WordPress configuration. Production Hostinger transfer not verified. Server credentials and deployment are still required; no browser receives a repository token.
- Installer 0.1.3: NotSigned, SHA-256 bd54bbf74b543903240f4a14da30db435fb2af722c2ca5296f209e30ab84f98d. Bundled runtime tests passed; Windows policy blocked setup. Installation/launch/uninstall on a clean laptop remain pending. No security controls bypassed.
- Application licence and runtime redistribution review remain pending; this is a private preview, not a claim of production readiness.

## 0.1.4 and theme 1.2.17 follow-up

- 47 application tests passed; both local candidate installers passed normal launch,
  two bundled smoke runs, source/runtime inventory and uninstall preservation.
- GitHub run 38582941797 passed build, bundled smoke, installation/uninstallation
  and explicit evaluation-preview publication. Version 0.1.4 remains unsigned.
- Public installer downloaded without authentication: 91,320,434 bytes; SHA-256
  f18d299257c5f7e92df3af4159e5a88f8faf7d4cedfe4ccaac09489373d8ff1a.
- Access plugin 0.2.1 and theme 1.2.17 released. Plugin acceptance/version/hash
  regression tests and local WordPress password/rotation/grant/rate tests passed.
- Local HTTP page showed both forms without disclosing the code; missing-code
  download returned 403; correct native password cookie unlocked the page while
  missing release acceptance kept delivery disabled. Synthetic images returned 200.
- Browser checks at mobile and desktop widths found no horizontal overflow.
- Downloaded theme/plugin ZIPs contained no checked sensitive paths or secret-pattern
  matches; theme ZIP excludes companion plugin/integration source directories.
- Live https://dascalasu.com/emailchronicle/ returned HTTP 404. Hostinger deployment
  and a working production website code were not completed or claimed.
- Source MIT licence selected under owner delegation. Trusted signing, independent
  clean-machine acceptance and remaining runtime redistribution review stay pending.
