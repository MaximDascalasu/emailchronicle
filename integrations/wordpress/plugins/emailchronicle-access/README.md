# EmailChronicle: request access or enter a code

Visitors see both options immediately on /emailchronicle/. Friends enter the shared code; other visitors submit the request form. Review requests under Tools > EmailChronicle access and manually email the code. Requests do not reveal the code or grant access automatically. No GitHub account is required for visitors.

## Deploy

1. Deploy the theme update and copy integrations/emailchronicle-access (or the app repository integrations/wordpress/plugins/emailchronicle-access) to wp-content/plugins/emailchronicle-access. Activate the plugin separately; it is not executable theme code and is not auto-installed.
2. Create/preserve the published page with slug emailchronicle and template page-emailchronicle.php. In Pages > EmailChronicle > Visibility choose Password protected and set a long random shared access code. The custom template intentionally displays both access options publicly; the code gates only the installer. Changing the code revokes old password cookies. The shared code can be forwarded.
3. Exclude this page and its admin-post actions from host/CDN caches. Require HTTPS. Test the request notification using WP Mail SMTP; no code is sent automatically. Administrator notifications default to WordPress admin_email.
4. Complete the clean-laptop acceptance checklist. v0.1.3 is unsigned and its setup was blocked on the development machine; Windows security controls must not be bypassed. Application licence and runtime redistribution decisions remain outstanding.
5. Create private storage OUTSIDE public_html, all document roots and wp-content. Configure the following in private server configuration (not theme settings, Git or browser JavaScript):

```php
define('EC_PRIVATE_DIR', '/absolute/private/emailchronicle');
define('EC_INSTALLER_PATH', EC_PRIVATE_DIR . '/EmailChronicle-Setup-0.1.3-x64.exe');
define('EC_INSTALLER_SHA256', 'bd54bbf74b543903240f4a14da30db435fb2af722c2ca5296f209e30ab84f98d');
// Fill the numeric release asset ID from the private GitHub release.
define('EC_GITHUB_ASSET_ID', 'REPLACE_WITH_ASSET_ID');
// Prefer EC_GITHUB_TOKEN environment variable: fine-grained token limited to
// MaximDascalasu/emailchronicle, Contents: read, with an expiry.
// Confirm only after laptop acceptance:
// define('EC_RELEASE_ACCEPTED', true);
```

6. Once acceptance is confirmed, set EC_RELEASE_ACCEPTED and use Tools > EmailChronicle access > Sync verified installer from GitHub. Only administrators can sync. The plugin checks the downloaded SHA-256 and stores a private copy; visitors receive that copy after code validation. Private GitHub credentials are never passed to visitors or the redirected asset host. Direct links to private GitHub would require GitHub sign-in, so they are not used in the visitor flow.
7. Verify unauthenticated downloads return 403, correct code can download the exact approved hash, changing the code denies old cookies, and private storage has no public URL. Large-file transfer depends on Hostinger PHP timeout/storage limits; verify the complete 91 MB transfer on production.

Leaving installer configuration absent keeps downloads disabled. The updated theme/plugin are deployment sources; pushing GitHub does not configure Hostinger or deploy WordPress automatically. Never put the installer in the theme or Media Library.
