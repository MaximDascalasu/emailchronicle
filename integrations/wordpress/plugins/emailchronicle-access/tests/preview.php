<?php
// Local WordPress only: php -d mysqli.default_port=PORT tests/preview.php /path/to/wp-load.php
if (PHP_SAPI!=='cli' || empty($argv[1])) exit(1);
require $argv[1];
if (wp_get_environment_type()!=='local') exit(1);
function preview_assert($ok,$label) { if (!$ok) throw new RuntimeException($label); echo "PASS: $label\n"; }
$page=get_page_by_path('emailchronicle',OBJECT,'page');
preview_assert($page instanceof WP_Post,'preview page exists');
require_once ABSPATH.WPINC.'/class-phpass.php';
$hasher=new PasswordHash(8,true); $cookie='wp-postpass_'.COOKIEHASH;
$original=$_COOKIE[$cookie] ?? null;
try {
    unset($_COOKIE[$cookie]);
    $html=EC_Access::preview();
    preview_assert(strpos($html,'Have an access code?')!==false && strpos($html,'Request access</h3>')!==false,'both choices shown immediately');
    preview_assert(strpos($html,'name="post_password"')!==false && strpos($html,'name="email"')!==false,'code and request inputs shown');
    $test=clone $page; $test->post_password='synthetic-code-for-testing';
    preview_assert(!EC_Access::preview_allowed($test),'missing cookie denied');
    $_COOKIE[$cookie]=$hasher->HashPassword('incorrect');
    preview_assert(!EC_Access::preview_allowed($test),'wrong code denied');
    $_COOKIE[$cookie]=$hasher->HashPassword($test->post_password);
    preview_assert(EC_Access::preview_allowed($test),'correct code accepted');
    $test->post_password='rotated-code';
    preview_assert(!EC_Access::preview_allowed($test),'code rotation revokes old cookie');
    $test->post_password='';
    preview_assert(!EC_Access::preview_allowed($test),'empty code fails closed');
} finally {
    if ($original===null) unset($_COOKIE[$cookie]); else $_COOKIE[$cookie]=$original;
}
