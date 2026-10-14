<?php
/** Template Name: EmailChronicle project */
if (!defined('ABSPATH')) { exit; }
get_header();
?>
<main id="main-content" class="ec-portal">
  <section class="ec-hero container">
    <div>
      <p class="eyebrow">EmailChronicle / Windows desktop</p>
      <h1>The conversation.<br><span>Back in order.</span></h1>
      <p class="ec-lead">Turn scattered email evidence into a chronological investigation. Search locally, inspect every source and share clear reports.</p>
      <ul class="ec-tags" aria-label="Application requirements"><li>Target: Windows 10/11 x64</li><li>Runs locally</li><li>Single bundled installer</li></ul>
      <div class="ec-actions"><a class="button" href="<?php echo (class_exists('EC_Access') && EC_Access::preview_allowed(get_queried_object())) ? '#early-access' : '#ec-code'; ?>">Enter access code</a><a class="button" href="#ec-request">Request access</a><a class="text-link" href="#how-it-works">See how it works →</a></div>
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
  <section class="ec-boundary"><div class="container"><strong>The website delivers the app. The desktop holds the evidence.</strong><p>No email upload, Gmail sign-in or case synchronisation is provided by this page. The development design uses local processing; the distributed release still requires independent testing. Your storage has its own settings. Original EML inspection uses the built-in read-only source viewer.</p></div></section>
  <section id="how-it-works" class="section container">
    <p class="eyebrow">Your first investigation</p><h2>A clear path through the evidence.</h2>
    <ol class="ec-steps"><li><b>01</b><h3>Install locally</h3><p>Download the Windows installer below, open setup, then launch EmailChronicle. No extra software is needed. If Windows blocks setup, stop and contact Maxim.</p></li><li><b>02</b><h3>Create a case</h3><p>Keep each investigation in a separate evidence collection.</p></li><li><b>03</b><h3>Import EML</h3><p>Add email files. Originals are preserved; known dates are converted to UTC.</p></li><li><b>04</b><h3>Review &amp; export</h3><p>Check uncertainty and provenance, then export the visible findings.</p></li></ol>
  </section>
  <section class="ec-capabilities container">
    <div><p class="eyebrow">Current development build</p><h2>Find the thread.<br>Keep the context.</h2><p>Features below describe the current development code. A preview installer may lag behind development. Feature availability and clean-machine compatibility must be verified for the approved build.</p></div>
    <div class="ec-feature-grid"><article><h3>Explainable search</h3><p>Exact terms, investigator-selected synonyms and spelling tolerance. Each match can explain its origin.</p></article><article><h3>Source-linked timelines</h3><p>UTC ordering, preserved evidence hashes, quoted-header labels and uncertainty flags.</p></article><article><h3>Reports &amp; visual exports</h3><p>PDF, Excel and CSV, plus timeline, Gantt-style event and communication graphs.</p></article><article><h3>Local investigations</h3><p>SQLite storage and a basic audit trail. No AI model or hosted processing required.</p></article></div>
  </section>
  <section class="section container" aria-labelledby="preview-gallery"><p class="eyebrow">Synthetic evidence only</p><h2 id="preview-gallery">Explore the preview workflow.</h2><p>Actual development UI screenshots below use synthetic emails and invented identities. Captured from v0.1.1 source, not a verified signed installer.</p><div class="ec-gallery">
    <figure><img src="<?php echo esc_url(get_template_directory_uri().'/assets/images/ec-timeline-synthetic.png'); ?>" alt="EmailChronicle development timeline showing synthetic messages, duplicate hints and missing-date review flags" loading="lazy"><figcaption>Synthetic timeline · source references and review flags.</figcaption></figure>
    <figure><img src="<?php echo esc_url(get_template_directory_uri().'/assets/images/ec-search-synthetic.png'); ?>" alt="EmailChronicle development search showing synthetic Phoenix payment results and selected synonym explanations" loading="lazy"><figcaption>Synthetic search · explainable matches.</figcaption></figure>
  </div></section>
  <section id="early-access" class="section container"><div class="ec-download"><div><p class="eyebrow">For invited friends</p><h2>Request access or enter your code.</h2><p>Already have a code? Enter it for the download. Otherwise, request access and Maxim can send you a code. One installer; no GitHub account or extra software needed.</p><ol><li>Download the Windows installer.</li><li>Open the installer and follow setup.</li><li>Launch EmailChronicle and try synthetic EML files first.</li></ol><p>Version 0.1.3 is unsigned. Windows policy blocked setup on the development computer; testing on another laptop is still required. Do not bypass Windows security controls. Downloads remain disabled until testing is complete.</p><p>Target: Windows 10/11 x64. Your investigation files stay in the desktop workspace. Preview software: EML import only; review uncertain dates and quoted headers before relying on results.</p><p>Need help? <a href="mailto:maximdascalasu@gmail.com">Contact Maxim</a>.</p></div><div><?php echo shortcode_exists('emailchronicle_access') ? do_shortcode('[emailchronicle_access]') : '<p>Preview download unavailable.</p>'; ?></div></div></section>
  <section class="ec-faq container section"><p class="eyebrow">Before you start</p><h2>Practical answers.</h2>
    <details><summary>Can I use Gmail messages?</summary><p>Yes. In Gmail, open an individual email and use its message menu → Download message. Import the resulting EML file. Direct Gmail connections and Takeout MBOX imports are not implemented.</p></details>
    <details><summary>How does this work on another computer?</summary><p>Install the app and start a new investigation with local EML files. Existing investigations do not synchronise through this website. A portable investigation package is planned; copying only the database can break evidence links.</p></details>
    <details><summary>Where is the investigation stored?</summary><p>By default, under <code>%LOCALAPPDATA%\EmailChronicle</code>. Back up the whole folder. Use a location outside synchronised folders if evidence must stay on the device. Uninstall retains investigation data.</p></details>
    <details><summary>What are the current limits?</summary><p>Import is EML only. MSG, PDF, DOCX and ZIP import are pending. The database is not encrypted and its audit trail is not tamper-proof. Quoted metadata and duplicate hints require investigator review; reports do not certify conclusions.</p></details>
    <details><summary>What if Windows blocks the installer?</summary><p>Do not disable organisation security controls. Ask your administrator to assess the release, or wait for a verified signed build. A local test certificate does not establish a publicly trusted publisher.</p></details>
  </section>
</main>
<?php get_footer(); ?>
