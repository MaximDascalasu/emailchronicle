# EmailChronicle website integration

The repository and existing GitHub release assets are public. A website code gates
only this WordPress endpoint; it cannot restrict public GitHub downloads.

1. Install the theme and the separate `emailchronicle-access` plugin. Create or
   preserve the published `emailchronicle` page with `page-emailchronicle.php`.
2. Set its WordPress page password to a long random shared code. The custom page
   shows both code entry and access requests publicly. Requests remain private;
   only administrators can inspect or delete them. No code is sent automatically.
3. Require HTTPS; exclude this page and admin-post handlers from all caches.
4. Keep installer storage outside every web root and `wp-content`. Configure the
   following only in private server configuration, never in Git or theme settings:

```php
define('EC_PRIVATE_DIR', '/absolute/private/emailchronicle');
define('EC_RELEASE_VERSION', '0.1.4');
define('EC_INSTALLER_PATH', EC_PRIVATE_DIR . '/EmailChronicle-Setup-0.1.4-x64.exe');
// Set EC_INSTALLER_SHA256 to the exact release checksum (64 lowercase hex digits).
// Set EC_GITHUB_ASSET_ID to that release's numeric installer asset ID.
// Set EC_RELEASE_ACCEPTED to true ONLY after reviewing installation acceptance.
```

5. After acceptance, an administrator can use Tools > EmailChronicle access >
   Sync verified installer from GitHub. Public assets need no GitHub token.
   If a token is required, use an expiring read-only repository credential in
   EC_GITHUB_TOKEN environment/private server settings. It is never sent to visitors
   or forwarded to the asset redirect host. Sync verifies SHA-256 before activation.
6. Every download rechecks acceptance, configured version, private path and checksum.
   Missing settings, modified bytes, stale versions or withdrawn acceptance disable
   delivery. Old password cookies stop working when the page password changes.
7. Test wrong/missing codes, correct-code exact-byte delivery, rotation, withdrawn
   acceptance, caching and the complete installer transfer on the production host.
   Configure administrator notification with WP Mail SMTP or private EC_SMTP_*
   settings. Do not email real applicants during synthetic tests.

Local checks: `php tests/release-gate.php` needs no WordPress. `tests/preview.php`
and `tests/access.php` require a running local WordPress and its wp-load.php path.

Pushing source or publishing a GitHub release does not deploy Hostinger files or
WordPress database settings. Production deployment and clean-machine acceptance
remain separate requirements. Access codes and server credentials stay outside Git.

## WordPress setup without hosting configuration edits (plugin 0.2.2)

Under Tools > EmailChronicle access, upload the verified 0.1.4 installer. The
administrator-only POST handler checks the pinned SHA-256, creates storage beside
(rather than inside) the document root, rejects public-root paths and moves the
file into private storage. PHP/hosting upload and filesystem limits still apply.
The upload leaves downloads disabled. Set a long shared code and explicitly enable
the unsigned evaluation preview after reviewing the tests. These settings are
stored in non-autoloaded WordPress options; environment/constants take precedence.
The code is saved as the native WordPress page password, never displayed in the
setup screen and never included in release assets. Request notifications use the
existing configured WordPress mail transport only when enabled; applicants are
reviewed manually and receive no automatic code.

The intended distribution is protected website delivery. Future application
workflows create draft releases and do not upload installer Actions artifacts in
the public repository. Existing public binaries must be retired after protected
website delivery is verified. Public MIT source remains available and can be built
independently; this restricts official binary downloads, not source redistribution.
