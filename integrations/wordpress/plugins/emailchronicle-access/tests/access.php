<?php
// Run only against a local WordPress: php -d mysqli.default_port=PORT tests/access.php /path/to/wp-load.php
if (PHP_SAPI!=='cli' || empty($argv[1])) exit(1);
require $argv[1];
if (wp_get_environment_type()!=='local') die("Local environment required.\n");
function ec_assert($condition,$label) { if (!$condition) throw new RuntimeException('FAIL: '.$label); echo 'PASS: '.$label."\n"; }
$id=wp_insert_post(['post_type'=>'ec_request','post_status'=>'private','post_title'=>'Synthetic access unit test']);
$token=bin2hex(random_bytes(32));
try {
    update_post_meta($id,'grant',['hash'=>hash('sha256',$token),'expires'=>time()+60]);
    update_post_meta($id,'state','pending'); ec_assert(!EC_Access::authorized($id,$token),'pending access denied');
    update_post_meta($id,'state','approved'); ec_assert(EC_Access::authorized($id,$token),'approved active token accepted');
    ec_assert(!EC_Access::authorized($id,bin2hex(random_bytes(32))),'wrong token denied');
    ec_assert(!EC_Access::authorized($id,''),'missing token denied');
    update_post_meta($id,'grant',['hash'=>hash('sha256',$token),'expires'=>time()-1]); ec_assert(!EC_Access::authorized($id,$token),'expired token denied');
    update_post_meta($id,'grant',['hash'=>hash('sha256',$token),'expires'=>time()+60]); update_post_meta($id,'state','revoked'); ec_assert(!EC_Access::authorized($id,$token),'revoked token denied');
    update_post_meta($id,'state','approved'); update_post_meta($id,'grant',['hash'=>hash('sha256',bin2hex(random_bytes(32))),'expires'=>time()+60]); ec_assert(!EC_Access::authorized($id,$token),'renewal invalidates previous token');
    $identity='synthetic-qa:'.bin2hex(random_bytes(16));
    ec_assert(!EC_Access::limited($identity,2),'first rate-limit attempt allowed');
    ec_assert(!EC_Access::limited($identity,2),'second rate-limit attempt allowed');
    ec_assert(EC_Access::limited($identity,2),'excess attempts rate limited');
    ec_assert(EC_Access::installer()===false,'downloads disabled without installer configuration');
} finally { wp_delete_post($id,true); }
