# EmailChronicle WordPress download portal

These files are installed in the local `dascalasu-ai-theme` theme. They are also
tracked here so the integration can be reviewed and moved to the live theme.
They reuse that theme's header, footer and editorial CSS. This is not a standalone
WordPress plugin or a replacement theme.

## Enable the page

1. Start the **max** site in Local. It returned HTTP 502 during implementation.
2. In WordPress, create a page called **EmailChronicle**, slug `emailchronicle`.
3. Select the **EmailChronicle download portal** template and publish the page
   on the local site. `page-emailchronicle.php` is also the automatic template
   for a page with this slug.
4. Preview `http://max.local/emailchronicle/`.
5. Add that page to the site's navigation or Toolkit when ready.

The local theme's `functions.php` now includes:

```php
require_once get_template_directory() . '/inc/emailchronicle.php';
```

To transfer the integration, copy `page-emailchronicle.php`, `inc/emailchronicle.php`
and `assets/css/emailchronicle.css` into the same theme on the destination, and
add the include once. Preserve the destination theme's existing files. Deploy
through your normal WordPress/theme workflow; these changes have not been
published to the live website or pushed to the separate theme repository.

## Configure a download

Open **Appearance → Customize → EmailChronicle downloads**:

- Installer HTTPS URL: an accessible release asset or dedicated download host.
- Installer version: the exact version of that binary.
- SHA-256: all 64 hexadecimal characters, obtained from the tested binary.
- Release notes HTTPS URL: notes for that particular release.
- Signing status: leave unsigned/pending unless the publisher has actually
  verified the production Authenticode signatures and timestamp.

The main download requires URL, version and a valid SHA-256. No network request
or automatic signature check is performed by the template. Configuration is the
publisher's responsibility. A checksum does not establish publisher identity.
The website cannot make an unsigned binary trusted. Never disable Windows or
organisation controls to distribute a blocked build.

Do not point a public download to a private GitHub asset unless visitors are
intended to have repository access. No repository token is stored in WordPress.
The fallback links authorised testers to the older v0.1.0 release and explains
its limitations. Current development features are labelled separately from that
older installer. Do not publish a current installer until clean-machine tests,
licensing/redistribution review and appropriate release signing are resolved.
Distribute required third-party notices and source companions alongside releases.

## Privacy and scope

The portal has no upload form, Gmail connection, evidence API, telemetry additions
or case synchronisation. It delivers software and documentation. The existing
website/host may have its own logging or plugins; this integration does not alter
those policies. Email evidence is processed by the desktop application.
Portable investigation packages remain planned, not implemented by this portal.

## Verification

PHP syntax checks passed for the template, integration module and modified theme
functions. Isolated pending/configured template rendering checks verified output
escaping, HTTPS/hash sanitisation and absence of upload UI. Live WordPress,
Customizer persistence, responsive browser layout and actual file downloads still
need verification after the Local site is started. Do not treat the static checks
as proof of a live deployment.
