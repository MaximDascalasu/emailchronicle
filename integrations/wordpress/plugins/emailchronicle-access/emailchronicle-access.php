<?php
/**
 * Plugin Name: EmailChronicle Early Access
 * Description: Request access or enter a shared code; private installer delivery.
 * Version: 0.2.5
 */
if (!defined('ABSPATH')) exit;
final class EC_Access {
    static function boot() {
        $saved=function_exists('get_option') ? get_option('ec_release_settings',[]) : [];
        foreach (['EC_PRIVATE_DIR','EC_INSTALLER_PATH'] as $key) {
            if (!defined($key) && !empty($saved[$key]) && is_string($saved[$key])) define($key,$saved[$key]);
        }
        add_action('init', [__CLASS__, 'register']);
        add_shortcode('emailchronicle_access', [__CLASS__, 'preview']);
        foreach (['admin_post_nopriv_ec_preview_download', 'admin_post_ec_preview_download'] as $hook) add_action($hook, [__CLASS__, 'preview_download']);
        add_action('template_redirect', function() {
            $post=get_queried_object();
            if (is_page('emailchronicle') || is_page_template('page-emailchronicle.php') || ($post instanceof WP_Post && has_shortcode($post->post_content,'emailchronicle_access'))) {
                if (!defined('DONOTCACHEPAGE')) define('DONOTCACHEPAGE',true);
                nocache_headers();
            }
        }, 0);
        foreach (['admin_post_nopriv_ec_request', 'admin_post_ec_request'] as $hook) add_action($hook, [__CLASS__, 'request']);
        foreach (['admin_post_nopriv_ec_download', 'admin_post_ec_download'] as $hook) add_action($hook, [__CLASS__, 'download']);
        add_action('admin_menu', function() { add_management_page('EmailChronicle access', 'EmailChronicle access', 'manage_options', 'ec-access', [__CLASS__, 'admin']); });
        add_action('admin_post_ec_decision', [__CLASS__, 'decision']);
        add_action('admin_post_ec_sync_release', [__CLASS__, 'sync_release']);
        add_action('admin_post_ec_upload_release', [__CLASS__, 'upload_release']);
        add_action('admin_post_ec_save_access', [__CLASS__, 'save_access']);
    }
    // The same WordPress password cookie protects both the page and the file endpoint.
    static function preview_allowed($page) {
        return $page instanceof WP_Post && $page->post_type === 'page'
            && $page->post_status === 'publish' && $page->post_name === 'emailchronicle'
            && $page->post_password !== '' && !post_password_required($page);
    }
    static function preview() {
        $page=get_page_by_path('emailchronicle',OBJECT,'page');
        if (!self::preview_allowed($page)) {
            $code=($page instanceof WP_Post && $page->post_password !== '')
                ? str_replace(['Password:', 'Enter'], ['Access code:', 'Unlock download'], get_the_password_form($page))
                : '<p>Code access is being configured.</p>';
            return '<div class="ec-access-options"><section aria-labelledby="ec-code"><h3 id="ec-code">Have an access code?</h3><p>Enter the code Maxim shared with you.</p>'.$code.'</section><section aria-labelledby="ec-request"><h3 id="ec-request">Request access</h3><p>No code yet? Send a request. Maxim can email you the code after reviewing it.</p>'.self::form().'</section></div>';
        }
        if (!self::installer()) return '<p role="status"><strong>Download coming soon.</strong> The administrator must complete private installer setup and preview acceptance.</p>';
        $url=add_query_arg('action','ec_preview_download',admin_url('admin-post.php'));
        return '<a class="button" href="'.esc_url($url).'">Download for Windows</a><p>Version '.esc_html(self::release_version()).' · Windows x64 · Preview</p>';
    }
    static function preview_download() {
        nocache_headers();
        header('Referrer-Policy: no-referrer');
        header('X-Robots-Tag: noindex, nofollow');
        if (wp_get_environment_type()!=='local' && !is_ssl()) self::fail('HTTPS required.',403);
        if (!self::preview_allowed(get_page_by_path('emailchronicle',OBJECT,'page'))) self::fail('Open the preview page and enter its password first.',403);
        $file=self::installer();
        if (!$file) self::fail('The preview download is not available yet.',503);
        $handle=fopen($file,'rb');
        if (!$handle) self::fail('Release unavailable.',503);
        header('Content-Type: application/octet-stream');
        header('X-Content-Type-Options: nosniff');
        header('Content-Disposition: attachment; filename="'.sanitize_file_name(basename($file)).'"');
        header('Content-Length: '.filesize($file));
        fpassthru($handle); fclose($handle); exit;
    }
    static function sync_release() {
        if (!current_user_can('manage_options')) self::fail('Administrator access required.',403);
        check_admin_referer('ec_sync_release');
        if (($_SERVER['REQUEST_METHOD'] ?? '')!=='POST') self::fail('POST required.',405);
        if (wp_get_environment_type()!=='local' && !is_ssl()) self::fail('HTTPS required.',403);
        if ((string)self::setting('EC_RELEASE_ACCEPTED')!=='1') self::fail('Installer acceptance must be confirmed before enabling downloads.',409);
        $token=self::setting('EC_GITHUB_TOKEN');
        $asset=self::setting('EC_GITHUB_ASSET_ID');
        $expected=self::setting('EC_INSTALLER_SHA256');
        if (!ctype_digit((string)$asset) || !preg_match('/^[a-f0-9]{64}$/',$expected) || !defined('EC_INSTALLER_PATH') || !defined('EC_PRIVATE_DIR')) self::fail('Configure private server release settings first.',409);
        $dir=realpath(EC_PRIVATE_DIR); $parent=realpath(dirname(EC_INSTALLER_PATH));
        $norm=function($p) { return strtolower(str_replace('\\','/',$p)); };
        if (!$dir || !$parent || !self::release_version() || $norm($dir)!==$norm($parent) || basename(EC_INSTALLER_PATH)!=='EmailChronicle-Setup-'.self::release_version().'-x64.exe') self::fail('Invalid private installer destination.',409);
        foreach ([ABSPATH,WP_CONTENT_DIR,($_SERVER['DOCUMENT_ROOT'] ?? ABSPATH)] as $root) {
            $resolved=realpath($root);
            if ($resolved && strpos(rtrim($norm($dir),'/').'/',rtrim($norm($resolved),'/').'/')===0) self::fail('Installer storage must be outside public web roots.',409);
        }
        $temp=tempnam($dir,'ec-release-');
        if (!$temp) self::fail('Private storage is not writable.',503);
        $ok=false;
        try {
            $api='https://api.github.com/repos/MaximDascalasu/emailchronicle/releases/assets/'.$asset;
            $headers=['Accept'=>'application/octet-stream'];
            if ($token) $headers['Authorization']='Bearer '.$token;
            $r=wp_remote_get($api,['headers'=>$headers,'redirection'=>0,'timeout'=>60,'stream'=>true,'filename'=>$temp]);
            if (is_wp_error($r)) throw new RuntimeException('GitHub download failed.');
            $status=wp_remote_retrieve_response_code($r);
            if ($status===302) {
                $location=wp_remote_retrieve_header($r,'location');
                $parts=wp_parse_url($location);
                if (!$parts || ($parts['scheme'] ?? '')!=='https' || !in_array(strtolower($parts['host'] ?? ''),['release-assets.githubusercontent.com','objects.githubusercontent.com'],true) || isset($parts['user']) || isset($parts['pass']) || isset($parts['port'])) throw new RuntimeException('Unexpected GitHub asset redirect.');
                // Fresh request: never forward the repository credential to the asset host.
                $r=wp_remote_get($location,['redirection'=>0,'timeout'=>120,'stream'=>true,'filename'=>$temp]);
                if (is_wp_error($r)) throw new RuntimeException('GitHub asset download failed.');
                $status=wp_remote_retrieve_response_code($r);
            }
            if ($status!==200 || !hash_equals($expected,hash_file('sha256',$temp))) throw new RuntimeException('Release response or SHA-256 did not match.');
            if (!rename($temp,EC_INSTALLER_PATH)) throw new RuntimeException('Cannot activate verified installer.');
            $ok=true;
        } catch (RuntimeException $e) {
            $message=$e->getMessage();
        } finally {
            if (is_file($temp)) unlink($temp);
        }
        if (!$ok) self::fail($message ?? 'Release download failed.',503);
        wp_safe_redirect(admin_url('tools.php?page=ec-access&ec_synced=1')); exit;
    }
    static function register() {
        register_post_type('ec_request', ['public'=>false, 'show_ui'=>false, 'supports'=>[], 'can_export'=>false, 'rewrite'=>false]);
    }
    static function value($key) { return isset($_POST[$key]) && is_string($_POST[$key]) ? trim(wp_unslash($_POST[$key])) : ''; }
    static function fail($message, $code=400) { wp_die(esc_html($message), 'EmailChronicle', ['response'=>$code]); }
    static function limited($identity, $limit) {
        global $wpdb;
        $bucket = (int) floor(time()/3600);
        $key = '_ec_rate_' . $bucket . '_' . hash_hmac('sha256', $identity, wp_salt('nonce'));
        // Atomic SQL counter: simultaneous submissions cannot bypass the limit.
        $result = $wpdb->query($wpdb->prepare("INSERT INTO {$wpdb->options} (option_name,option_value,autoload) VALUES (%s,'1','no') ON DUPLICATE KEY UPDATE option_value=CAST(option_value AS UNSIGNED)+1", $key));
        if ($result === false) return true;
        $count = (int) $wpdb->get_var($wpdb->prepare("SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", $key));
        $wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name LIKE %s AND option_name < %s", $wpdb->esc_like('_ec_rate_').'%', '_ec_rate_'.($bucket-48).'_'));
        return $count > $limit;
    }
    static function form() {
        nocache_headers();
        $stamp = time();
        ob_start(); ?>
        <form class="ec-access-form" method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
          <p>We collect your name, email, optional organisation and intended use to assess preview suitability and contact you about your request and access. Requests are reviewed manually; submission does not grant access. Do not include client names, investigation evidence or confidential case details. No file uploads are accepted. Ask the site administrator to delete your request when no longer needed.</p>
          <?php if (isset($_GET['ec_requested'])) : ?><p role="status">Your request has been received. Maxim will review it and can email you an access code.</p><?php endif; ?>
          <input type="hidden" name="action" value="ec_request">
          <?php wp_nonce_field('ec_request'); ?>
          <input type="hidden" name="started" value="<?php echo esc_attr($stamp); ?>"><input type="hidden" name="proof" value="<?php echo esc_attr(hash_hmac('sha256', (string)$stamp, wp_salt('nonce'))); ?>">
          <div class="ec-trap" aria-hidden="true"><label>Leave blank<input name="website" tabindex="-1" autocomplete="off"></label></div>
          <label>Name <span>(required)</span><input name="name" autocomplete="name" maxlength="120" required></label>
          <label>Email <span>(required)</span><input name="email" type="email" autocomplete="email" maxlength="254" required></label>
          <label>Organisation <span>(optional)</span><input name="organisation" autocomplete="organization" maxlength="160"></label>
          <label>Intended use <span>(required; no evidence or confidential details)</span><textarea name="intended_use" maxlength="2000" rows="4" required></textarea></label>
          <label class="ec-ack"><input name="preview" type="checkbox" value="1" required> I understand this is preview software with limitations and unverified production signing, and that access requires manual approval.</label>
          <button class="button" type="submit">Request access</button>
        </form>
        <?php return ob_get_clean();
    }
    static function request() {
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') self::fail('POST required.',405);
        if (wp_get_environment_type()!=='local' && !is_ssl()) self::fail('HTTPS required.',403);
        if (self::limited('ip:'.($_SERVER['REMOTE_ADDR'] ?? 'unknown'), 8)) self::fail('Too many attempts. Please try again in an hour.',429);
        if (!wp_verify_nonce(self::value('_wpnonce'),'ec_request')) self::fail('Form expired. Reload and try again.',403);
        $stamp=self::value('started');
        if (!ctype_digit($stamp) || !hash_equals(hash_hmac('sha256',$stamp,wp_salt('nonce')), self::value('proof')) || time()-(int)$stamp < 3 || time()-(int)$stamp > 7200 || self::value('website') !== '' || !empty($_FILES)) self::fail('Request could not be accepted. Reload the form and try again.');
        $name=sanitize_text_field(self::value('name')); $email=self::value('email'); $org=sanitize_text_field(self::value('organisation')); $use=sanitize_textarea_field(self::value('intended_use'));
        if (!$name || strlen($name)>120 || !is_email($email) || strlen($email)>254 || strlen($org)>160 || !$use || strlen($use)>2000 || self::value('preview')!=='1') self::fail('Complete the required fields and preview acknowledgement within the stated limits.');
        if (self::limited('email:'.strtolower($email),3)) self::fail('Too many requests. Please try again in an hour.',429);
        $id=wp_insert_post(['post_type'=>'ec_request','post_status'=>'private','post_title'=>$name,'meta_input'=>['email'=>$email,'organisation'=>$org,'intended_use'=>$use,'state'=>'pending','acknowledged_at'=>time()]],true);
        if (is_wp_error($id) || !$id) self::fail('Unable to save the request. Please try later.',503);
        // Notify the administrator only; the shared code is sent manually after review.
        self::mail(get_option('admin_email'),'EmailChronicle request pending','A request awaits manual review: '.admin_url('tools.php?page=ec-access'), $id);
        wp_safe_redirect(add_query_arg('ec_requested','1',home_url('/emailchronicle/')).'#early-access',303); exit;
    }
    static function installer() {
        if ((string)self::setting('EC_RELEASE_ACCEPTED')!=='1') return false;
        $expected=self::setting('EC_INSTALLER_SHA256');
        if (!preg_match('/^[a-f0-9]{64}$/',$expected) || !self::release_version()) return false;
        if (!defined('EC_INSTALLER_PATH') || !defined('EC_PRIVATE_DIR')) return false;
        $file=realpath(EC_INSTALLER_PATH); $dir=realpath(EC_PRIVATE_DIR); $public=realpath(ABSPATH);
        if (!$file || !$dir || !$public || !is_file($file) || !is_readable($file)) return false;
        if (basename($file)!=='EmailChronicle-Setup-'.self::release_version().'-x64.exe') return false;
        $norm=function($p) { return strtolower(str_replace('\\','/',$p)); };
        $f=$norm($file); $d=rtrim($norm($dir),'/').'/'; $p=rtrim($norm($public),'/').'/';
        if (strpos($f,$d)!==0 || !preg_match('/\.(exe|msi|zip)$/i',$file)) return false;
        $roots=[$public, WP_CONTENT_DIR];
        if (!empty($_SERVER['DOCUMENT_ROOT'])) $roots[]=$_SERVER['DOCUMENT_ROOT'];
        foreach ($roots as $root) {
            $resolved=realpath($root);
            if (!$resolved) continue;
            $boundary=rtrim($norm($resolved),'/').'/';
            if (strpos($d,$boundary)===0 || strpos($f,$boundary)===0) return false;
        }
        // Every serving path honors acceptance, release version and approved bytes.
        if (!hash_equals($expected,hash_file('sha256',$file))) return false;
        return $file;
    }
    static function release_version() {
        $version=(string)(self::setting('EC_RELEASE_VERSION') ?: '0.1.7');
        return preg_match('/^\d+\.\d+\.\d+$/D',$version) ? $version : '';
    }
    static function setting($key) {
        if (getenv($key)!==false) return getenv($key);
        if (defined($key)) return constant($key);
        $allowed=['EC_PRIVATE_DIR','EC_INSTALLER_PATH','EC_INSTALLER_SHA256','EC_RELEASE_VERSION','EC_RELEASE_ACCEPTED','EC_MAIL_READY'];
        $saved=function_exists('get_option') ? get_option('ec_release_settings',[]) : [];
        return in_array($key,$allowed,true) && is_array($saved) ? ($saved[$key] ?? '') : '';
    }
    static function private_directory_valid($directory) {
        $dir=realpath($directory);
        if (!$dir) return false;
        $norm=function($p) { return rtrim(strtolower(str_replace('\\','/',$p)),'/').'/'; };
        foreach ([ABSPATH,WP_CONTENT_DIR,($_SERVER['DOCUMENT_ROOT'] ?? ABSPATH)] as $root) {
            $resolved=realpath($root);
            if ($resolved && strpos($norm($dir),$norm($resolved))===0) return false;
        }
        return true;
    }
    static function setup_guard($nonce) {
        if (!current_user_can('manage_options')) self::fail('Administrator access required.',403);
        if (($_SERVER['REQUEST_METHOD'] ?? '')!=='POST') self::fail('POST required.',405);
        if (wp_get_environment_type()!=='local' && !is_ssl()) self::fail('HTTPS required.',403);
        check_admin_referer($nonce);
    }
    static function upload_release() {
        self::setup_guard('ec_upload_release');
        $upload=$_FILES['installer'] ?? [];
        if (!is_array($upload) || ($upload['error'] ?? -1)!==UPLOAD_ERR_OK || !is_string($upload['tmp_name'] ?? null) || !is_uploaded_file($upload['tmp_name']) || filesize($upload['tmp_name'])>150*1024*1024) self::fail('Choose the verified installer, up to 150 MB. Check the server upload limit.',400);
        $expected='4a0851dc6adecc56dc6adb6bde1881081126cc978c9bb279b7f10960a172281e';
        if (!hash_equals($expected,hash_file('sha256',$upload['tmp_name']))) self::fail('Installer checksum does not match the packaged 0.1.7 build.',400);
        $web=realpath($_SERVER['DOCUMENT_ROOT'] ?? ABSPATH);
        if (!$web || dirname($web)===$web) self::fail('Cannot determine private storage. Configure hosting storage first.',409);
        $dir=dirname($web).'/emailchronicle-private';
        if (!is_dir($dir) && !mkdir($dir,0700,true)) self::fail('Hosting does not allow private storage here. Contact the administrator.',409);
        if (!self::private_directory_valid($dir) || !is_writable($dir)) self::fail('Private storage is unavailable or inside a public web root.',409);
        $dir=realpath($dir); $file=$dir.'/EmailChronicle-Setup-0.1.7-x64.exe';
        $temp=tempnam($dir,'ec-upload-');
        if (!$temp) self::fail('Cannot stage private installer.',503);
        if (!move_uploaded_file($upload['tmp_name'],$temp)) { unlink($temp); self::fail('Private upload failed.',503); }
        chmod($temp,0600);
        if (!hash_equals($expected,hash_file('sha256',$temp)) || !rename($temp,$file)) { if (is_file($temp)) unlink($temp); self::fail('Cannot activate verified private file.',503); }
        update_option('ec_release_settings',['EC_PRIVATE_DIR'=>$dir,'EC_INSTALLER_PATH'=>$file,'EC_INSTALLER_SHA256'=>$expected,'EC_RELEASE_VERSION'=>'0.1.7','EC_RELEASE_ACCEPTED'=>false,'EC_MAIL_READY'=>self::setting('EC_MAIL_READY')],false);
        wp_safe_redirect(admin_url('tools.php?page=ec-access&ec_uploaded=1')); exit;
    }
    static function save_access() {
        self::setup_guard('ec_save_access');
        $page=get_page_by_path('emailchronicle',OBJECT,'page');
        if (!$page instanceof WP_Post || !current_user_can('edit_post',$page->ID)) self::fail('Create the EmailChronicle page first.',409);
        $code=self::value('access_code');
        if ($code!=='' && (strlen($code)<20 || strlen($code)>128)) self::fail('Use an access code of 20–128 characters.',400);
        if ($code==='' && $page->post_password==='') self::fail('Set an access code before enabling downloads.',409);
        if ($code!=='') {
            $result=wp_update_post(wp_slash(['ID'=>$page->ID,'post_password'=>$code]),true);
            if (is_wp_error($result)) self::fail('Cannot save access code.',503);
        }
        $saved=get_option('ec_release_settings',[]);
        if (!is_array($saved)) $saved=[];
        $saved['EC_RELEASE_ACCEPTED']=self::value('accepted')==='1';
        $saved['EC_MAIL_READY']=self::value('mail_ready')==='1';
        update_option('ec_release_settings',$saved,false);
        wp_safe_redirect(admin_url('tools.php?page=ec-access&ec_saved=1')); exit;
    }
    static function setup_screen() {
        $page=get_page_by_path('emailchronicle',OBJECT,'page');
        echo '<div class="wrap"><h1>EmailChronicle access setup</h1><p>Visitors can enter your shared code or request one. Requests remain private and require manual review; no code is sent automatically.</p>';
        if (isset($_GET['ec_uploaded'])) echo '<div class="notice notice-success"><p>Verified installer stored outside the public web root. Downloads remain disabled until you save an access code and enable the preview below.</p></div>';
        if (isset($_GET['ec_saved'])) echo '<div class="notice notice-success"><p>Access settings saved.</p></div>';
        echo '<p><strong>Private installer:</strong> '.(self::setting('EC_INSTALLER_PATH') && is_file(self::setting('EC_INSTALLER_PATH')) ? 'Stored' : 'Not uploaded').' · <strong>Download status:</strong> '.(self::installer() ? 'Enabled' : 'Disabled').'</p>';
        echo '<h2>1. Upload the verified installer</h2><p>Upload EmailChronicle-Setup-0.1.7-x64.exe. SHA-256 is checked before storage. This does not use the Media Library. Uploading disables downloads until you enable them again.</p><form method="post" enctype="multipart/form-data" action="'.esc_url(admin_url('admin-post.php')).'">';
        wp_nonce_field('ec_upload_release');
        echo '<input type="hidden" name="action" value="ec_upload_release"><input type="file" name="installer" accept=".exe" required aria-label="Verified Windows installer"><button class="button">Upload to private storage</button></form><h2>2. Access code and evaluation downloads</h2><p>Choose a long random code. Leave blank to preserve an existing code. Changing it revokes previous password cookies. The code is never displayed here.</p><p><strong>Code:</strong> '.($page instanceof WP_Post && $page->post_password!=='' ? 'Configured' : 'Not configured').'</p><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        wp_nonce_field('ec_save_access');
        echo '<input type="hidden" name="action" value="ec_save_access"><p><label>New access code <input type="password" name="access_code" autocomplete="new-password" minlength="20" maxlength="128"></label></p><p><label><input type="checkbox" name="accepted" value="1" '.checked((string)self::setting('EC_RELEASE_ACCEPTED'),'1',false).'> Enable this unsigned evaluation preview. I have reviewed the installer tests and accept it for invited evaluation; independent clean-machine testing and trusted signing remain pending.</label></p><p><label><input type="checkbox" name="mail_ready" value="1" '.checked((string)self::setting('EC_MAIL_READY'),'1',false).'> Use the configured WordPress email transport for administrator request notifications.</label></p><button class="button button-primary">Save access settings</button></form><p><a href="'.esc_url(home_url('/emailchronicle/')).'">Open visitor page</a></p></div>';
    }
    static function mail($to,$subject,$body,$id) {
        // Configure WP Mail SMTP outside the theme, or EC_SMTP_* environment settings.
        $host=self::setting('EC_SMTP_HOST');
        $local=wp_get_environment_type()==='local';
        if ($host) {
            if (!$local && (!self::setting('EC_SMTP_USER') || !self::setting('EC_SMTP_PASSWORD') || !is_email(self::setting('EC_SMTP_FROM')))) {
                update_post_meta($id,'mail_status','SMTP configuration incomplete'); return false;
            }
            // Use WordPress-bundled PHPMailer for an explicitly configured isolated transport.
            // This prevents another mail plugin/provider from overriding the local mail catcher.
            require_once ABSPATH.WPINC.'/PHPMailer/PHPMailer.php';
            require_once ABSPATH.WPINC.'/PHPMailer/SMTP.php';
            require_once ABSPATH.WPINC.'/PHPMailer/Exception.php';
            try {
                $m=new \PHPMailer\PHPMailer\PHPMailer(true);
                $m->isSMTP(); $m->Host=$host; $m->Port=(int)(self::setting('EC_SMTP_PORT') ?: 587);
                $m->SMTPAuth=!$local; $m->Username=self::setting('EC_SMTP_USER'); $m->Password=self::setting('EC_SMTP_PASSWORD');
                $m->SMTPSecure=$local ? '' : 'tls'; $m->SMTPAutoTLS=!$local; $m->Timeout=10;
                $m->setFrom(self::setting('EC_SMTP_FROM') ?: 'preview@example.test','EmailChronicle');
                $m->addAddress($to); $m->Subject=$subject; $m->Body=$body; $m->CharSet='UTF-8'; $ok=$m->send();
            } catch (\Exception $e) { $ok=false; }
        } elseif ((string)self::setting('EC_MAIL_READY')!=='1') { update_post_meta($id,'mail_status','Not configured'); return false; }
        else { $ok=wp_mail($to,$subject,$body); }
        update_post_meta($id,'mail_status',$ok ? 'Accepted by mail transport; delivery unconfirmed' : 'Failed');
        return $ok;
    }
    static function decision() {
        if (!current_user_can('manage_options')) self::fail('Administrator access required.',403);
        check_admin_referer('ec_decision');
        if (($_SERVER['REQUEST_METHOD'] ?? '')!=='POST') self::fail('POST required.',405);
        $id=absint(self::value('request_id')); $action=self::value('decision');
        if (get_post_type($id)!=='ec_request' || !in_array($action,['approve','revoke','delete'],true)) self::fail('Invalid request.');
        if ($action==='delete') { wp_delete_post($id,true); }
        elseif ($action==='revoke') { update_post_meta($id,'state','revoked'); delete_post_meta($id,'grant'); }
        else {
            if (!self::installer()) self::fail('Configure a readable installer outside the public web root before approving.',409);
            if (wp_get_environment_type()!=='local' && !is_ssl()) self::fail('HTTPS required for access delivery.',409);
            // A single record holds the complete grant, replaced on renewal; raw tokens are never stored.
            $token=bin2hex(random_bytes(32)); $expires=time()+DAY_IN_SECONDS;
            update_post_meta($id,'grant',['hash'=>hash('sha256',$token),'expires'=>$expires,'file_hash'=>hash_file('sha256',self::installer())]);
            update_post_meta($id,'state','approved');
            $url=add_query_arg(['action'=>'ec_download','request'=>$id,'token'=>$token],admin_url('admin-post.php'));
            if (!self::mail(get_post_meta($id,'email',true),'EmailChronicle preview access approved',"Your preview request was approved. This private bearer link expires in 24 hours. Do not forward it.\n\n".$url."\n\nSHA-256: ".hash_file('sha256',self::installer())."\nProduction signing has not been verified. Do not bypass organisational security controls.",$id)) {
                update_post_meta($id,'state','pending'); delete_post_meta($id,'grant'); self::fail('Email could not be sent. Access remains pending. Configure delivery and approve again.',503);
            }
        }
        if ($action!=='delete') { update_post_meta($id,'reviewed_by',get_current_user_id()); update_post_meta($id,'reviewed_at',time()); }
        wp_safe_redirect(admin_url('tools.php?page=ec-access')); exit;
    }
    static function authorized($id,$token) {
        $g=get_post_meta($id,'grant',true);
        return get_post_type($id)==='ec_request' && get_post_meta($id,'state',true)==='approved' && is_array($g) && ($g['expires'] ?? 0)>time() && preg_match('/^[a-f0-9]{64}$/',$token) && hash_equals($g['hash'] ?? '',hash('sha256',$token));
    }
    static function download() {
        nocache_headers(); header('Referrer-Policy: no-referrer'); header('X-Robots-Tag: noindex, nofollow');
        if (wp_get_environment_type()!=='local' && !is_ssl()) self::fail('HTTPS required.',403);
        $id=isset($_GET['request']) && is_scalar($_GET['request']) ? absint($_GET['request']) : 0;
        $token=isset($_GET['token']) && is_string($_GET['token']) ? $_GET['token'] : '';
        if (!self::authorized($id,$token)) self::fail('This access link is invalid, expired or revoked.',403);
        $file=self::installer(); $grant=get_post_meta($id,'grant',true);
        if (!$file || !hash_equals($grant['file_hash'],hash_file('sha256',$file))) self::fail('This approved release is unavailable. Please contact the administrator.',503);
        $handle=fopen($file,'rb'); if (!$handle) self::fail('Release unavailable.',503);
        header('Content-Type: application/octet-stream'); header('X-Content-Type-Options: nosniff'); header('Content-Disposition: attachment; filename="'.sanitize_file_name(basename($file)).'"'); header('Content-Length: '.filesize($file));
        fpassthru($handle); fclose($handle); exit;
    }
    static function admin() {
        if (!current_user_can('manage_options')) return;
        self::setup_screen();
        if (self::setting('EC_GITHUB_ASSET_ID')) {
        echo '<div class="wrap"><h2>GitHub installer storage</h2><p>Administrator-only sync downloads the private GitHub asset to private server storage and checks its configured SHA-256. Visitors never receive the GitHub credential. Enable only after installer acceptance.</p><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        wp_nonce_field('ec_sync_release');
        echo '<input type="hidden" name="action" value="ec_sync_release"><button class="button" type="submit">Sync verified installer from GitHub</button></form></div>';
        }
        echo '<div class="wrap"><h1>EmailChronicle access</h1><p>Review requests below, then manually email the shared page access code to applicants you accept. Set or rotate that code under Pages → EmailChronicle → Visibility → Password protected. Friends with the code can download without requesting access. Changing the shared code revokes previous password cookies. Delete removes request data.</p><p>Installer: '.(self::installer() ? 'Private file configured' : 'Unavailable — configure EC_PRIVATE_DIR and EC_INSTALLER_PATH outside the web root').'</p><table class="widefat"><thead><tr><th>Applicant</th><th>Intended use</th><th>Access / email</th><th>Decision</th></tr></thead><tbody>';
        foreach (get_posts(['post_type'=>'ec_request','post_status'=>'private','numberposts'=>100,'orderby'=>'date']) as $p) {
            $id=$p->ID; $g=get_post_meta($id,'grant',true); $state=get_post_meta($id,'state',true);
            echo '<tr><td>'.esc_html($p->post_title).'<br>'.esc_html(get_post_meta($id,'email',true)).'<br>'.esc_html(get_post_meta($id,'organisation',true)).'</td><td>'.nl2br(esc_html(get_post_meta($id,'intended_use',true))).'</td><td>'.esc_html($state);
            if ($state==='approved' && is_array($g)) echo '<br>'.esc_html($g['expires']<=time() ? 'Expired' : 'Expires '.gmdate('Y-m-d H:i',$g['expires']).' UTC');
            echo '<br>'.esc_html(get_post_meta($id,'mail_status',true)).'</td><td><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">'; wp_nonce_field('ec_decision');
            echo '<input type="hidden" name="action" value="ec_decision"><input type="hidden" name="request_id" value="'.esc_attr($id).'"><button class="button" name="decision" value="revoke">Revoke</button> <button class="button" name="decision" value="delete">Delete</button></form></td></tr>';
        }
        echo '</tbody></table><p>Showing the newest 100 requests.</p></div>';
    }
}
EC_Access::boot();
