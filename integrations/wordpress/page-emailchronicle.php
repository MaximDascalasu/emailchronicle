<?php
/** Template Name: EmailChronicle download portal */
if (!defined('ABSPATH')) { exit; }
$installer = dascalasu_ai_emailchronicle_https(get_theme_mod('emailchronicle_installer_url', ''));
$version = sanitize_text_field(get_theme_mod('emailchronicle_version', ''));
$hash = dascalasu_ai_emailchronicle_hash(get_theme_mod('emailchronicle_sha256', ''));
$notes = dascalasu_ai_emailchronicle_https(get_theme_mod('emailchronicle_release_notes_url', ''));
$signed = get_theme_mod('emailchronicle_signing_status', 'unsigned') === 'signed';
$ready = $installer !== '' && $version !== '' && $hash !== '';
get_header();
?>
<main id="main-content" class="ec-portal">
  <section class="ec-hero container">
    <div>
      <p class="eyebrow">EmailChronicle / Windows desktop</p>
      <h1>The conversation.<br><span>Back in order.</span></h1>
      <p class="ec-lead">Turn scattered email evidence into a chronological investigation. Search locally, inspect every source and share clear reports.</p>
      <ul class="ec-tags" aria-label="Application requirements"><li>Windows 10/11 x64</li><li>Runs locally</li><li>No Python needed for installer</li></ul>
      <div class="ec-actions"><a class="button" href="#download">Get EmailChronicle <span aria-hidden="true">↓</span></a><a class="text-link" href="#how-it-works">See how it works →</a></div>
      <p class="ec-small">This website distributes software. Your investigation emails stay in your desktop workspace.</p>
    </div>
    <div class="ec-console" aria-label="Illustrative desktop workflow">
      <div class="ec-console-top"><span>EC / EmailChronicle</span><span>Local workspace</span></div>
      <p class="ec-console-label">ILLUSTRATIVE EXAMPLE · SYNTHETIC EMAILS</p>
      <h2>One conversation. Every source.</h2>
      <ol class="ec-events"><li><time>09:00 UTC</time><div><strong>Initial request</strong><small>Original email metadata</small></div></li><li><time>10:30 UTC</time><div><strong>Follow-up reply</strong><small>Linked to preserved EML evidence</small></div></li><li class="ec-review"><span>Undated</span><div><strong>Forwarded extract</strong><small>Quoted headers · manual review required</small></div></li></ol>
      <div class="ec-console-footer">Source references / SHA-256 / Review flags</div>
    </div>
  </section>
  <section class="ec-boundary"><div class="container"><strong>The website delivers the app. The desktop holds the evidence.</strong><p>No email upload, Gmail sign-in or case synchronisation is provided by this page. The app makes no cloud or external AI calls; your storage and external mail viewer have their own settings.</p></div></section>
  <section id="how-it-works" class="section container">
    <p class="eyebrow">From download to investigation</p><h2>A clear path through the evidence.</h2>
    <ol class="ec-steps"><li><b>01</b><h3>Install locally</h3><p>Download the Windows installer, check its checksum and follow setup.</p></li><li><b>02</b><h3>Create a case</h3><p>Keep each investigation in a separate evidence collection.</p></li><li><b>03</b><h3>Import EML</h3><p>Add email files. Originals are preserved; known dates are converted to UTC.</p></li><li><b>04</b><h3>Review &amp; export</h3><p>Check uncertainty and provenance, then export the visible findings.</p></li></ol>
  </section>
  <section class="ec-capabilities container">
    <div><p class="eyebrow">Current development build</p><h2>Find the thread.<br>Keep the context.</h2><p>Features below describe the current development code. The older v0.1.0 preview installer does not include every recent improvement.</p></div>
    <div class="ec-feature-grid"><article><h3>Explainable search</h3><p>Exact terms, investigator-selected synonyms and spelling tolerance. Each match can explain its origin.</p></article><article><h3>Source-linked timelines</h3><p>UTC ordering, preserved evidence hashes, quoted-header labels and uncertainty flags.</p></article><article><h3>Reports &amp; visual exports</h3><p>PDF, Excel and CSV, plus timeline, Gantt-style event and communication graphs.</p></article><article><h3>Local investigations</h3><p>SQLite storage and a basic audit trail. No AI model or hosted processing required.</p></article></div>
  </section>
  <section id="download" class="section container">
    <div class="ec-download"><div><p class="eyebrow">Windows download</p><h2><?php echo $ready ? 'EmailChronicle ' . esc_html($version) : 'Current installer being prepared'; ?></h2>
    <?php if ($ready) : ?>
      <p><?php echo $signed ? 'Publisher reports production signature verification. Check the publisher shown by Windows before installation.' : 'Unsigned preview. Windows may show warnings or block execution. This is not a verified production release.'; ?></p>
      <a class="button" href="<?php echo esc_url($installer); ?>">Download Windows x64 installer ↓</a>
      <p class="ec-small">The download host may require authorisation. Installation is per user; packaged Python and Qt are included.</p>
    <?php else : ?>
      <p>A current tested installer is not configured here yet. Signing and clean-machine verification remain pending. No unavailable or unverified release is presented as a finished download.</p>
      <p><a class="text-link" href="https://github.com/MaximDascalasu/emailchronicle/releases/tag/v0.1.0" rel="noopener noreferrer">Authorised testers: older unsigned v0.1.0 preview →</a></p>
      <p class="ec-small">Private GitHub repository: sign-in and repository access required. The old preview has incomplete third-party notices and should not be redistributed as a reviewed commercial package.</p>
    <?php endif; ?>
    <?php if ($notes !== '') : ?><p><a href="<?php echo esc_url($notes); ?>">Read release notes</a></p><?php endif; ?>
    </div><div class="ec-checksum"><h3>Verify your download</h3><p>In PowerShell, run this on the actual downloaded file and compare its SHA-256 with the release value.</p><pre><code>Get-FileHash .\YourDownloadedInstaller.exe -Algorithm SHA256</code></pre>
    <?php if ($ready) : ?><p><strong>Expected SHA-256</strong></p><code class="ec-hash"><?php echo esc_html($hash); ?></code><?php else : ?><p class="ec-small">A checksum will appear when a current installer is configured. A checksum checks bytes; it does not establish publisher identity.</p><?php endif; ?>
    </div></div>
  </section>
  <section class="ec-faq container section"><p class="eyebrow">Before you start</p><h2>Practical answers.</h2>
    <details><summary>Can I use Gmail messages?</summary><p>Yes. In Gmail, open an individual email and use its message menu → Download message. Import the resulting EML file. Direct Gmail connections and Takeout MBOX imports are not implemented.</p></details>
    <details><summary>How does this work on another computer?</summary><p>Install the app and start a new investigation with local EML files. Existing investigations do not synchronise through this website. A portable investigation package is planned; copying only the database can break evidence links.</p></details>
    <details><summary>Where is the investigation stored?</summary><p>By default, under <code>%LOCALAPPDATA%\EmailChronicle</code>. Back up the whole folder. Use a location outside synchronised folders if evidence must stay on the device. Uninstall retains investigation data.</p></details>
    <details><summary>What are the current limits?</summary><p>Import is EML only. MSG, PDF, DOCX and ZIP import are pending. The database is not encrypted and its audit trail is not tamper-proof. Quoted metadata and duplicate hints require investigator review; reports do not certify conclusions.</p></details>
    <details><summary>What if Windows blocks the installer?</summary><p>Do not disable organisation security controls. Ask your administrator to assess the release, or wait for a verified signed build. A local test certificate does not establish a publicly trusted publisher.</p></details>
  </section>
</main>
<?php get_footer(); ?>
