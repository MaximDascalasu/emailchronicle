<?php
// Standalone CLI regression: no WordPress database or real installer needed.
if (PHP_SAPI !== 'cli') exit(1);
function add_action(...$args) {}
function add_shortcode(...$args) {}
function get_option($key,$default=[]) { return $GLOBALS['fake_settings'] ?? $default; }
function gate_assert($ok, $label) {
    if (!$ok) throw new RuntimeException($label);
    echo "PASS: $label\n";
}
$root=sys_get_temp_dir().'/ec-gate-'.bin2hex(random_bytes(8));
mkdir($root); mkdir($root.'/public'); mkdir($root.'/private');
define('ABSPATH', $root.'/public/');
define('WP_CONTENT_DIR', ABSPATH.'wp-content');
define('EC_PRIVATE_DIR', $root.'/private');
define('EC_INSTALLER_PATH', EC_PRIVATE_DIR.'/EmailChronicle-Setup-0.1.4-x64.exe');
file_put_contents(EC_INSTALLER_PATH, 'synthetic installer bytes');
require dirname(__DIR__).'/emailchronicle-access.php';
$keys=['EC_RELEASE_ACCEPTED','EC_INSTALLER_SHA256','EC_RELEASE_VERSION'];
$saved=[];
foreach ($keys as $key) { $saved[$key]=getenv($key); putenv($key); }
try {
    gate_assert(EC_Access::installer()===false, 'unaccepted configured file denied');
    putenv('EC_RELEASE_ACCEPTED=1');
    gate_assert(EC_Access::installer()===false, 'missing approved hash denied');
    putenv('EC_INSTALLER_SHA256='.hash_file('sha256',EC_INSTALLER_PATH));
    gate_assert(EC_Access::installer()===realpath(EC_INSTALLER_PATH), 'accepted matching release allowed');
    file_put_contents(EC_INSTALLER_PATH, 'changed bytes');
    gate_assert(EC_Access::installer()===false, 'changed installer denied');
    file_put_contents(EC_INSTALLER_PATH, 'synthetic installer bytes');
    putenv('EC_RELEASE_VERSION=0.1.3');
    gate_assert(EC_Access::installer()===false, 'stale release version denied');
    putenv('EC_RELEASE_VERSION=../0.1.4');
    gate_assert(EC_Access::installer()===false, 'invalid release version denied');
    putenv('EC_RELEASE_VERSION=0.1.4');
    gate_assert(EC_Access::installer()===realpath(EC_INSTALLER_PATH), 'configured current version allowed');
    putenv('EC_RELEASE_ACCEPTED=0');
    gate_assert(EC_Access::installer()===false, 'withdrawn acceptance immediately denies file');
    gate_assert(EC_Access::private_directory_valid($root.'/private'), 'private sibling directory allowed');
    gate_assert(!EC_Access::private_directory_valid($root.'/public'), 'document root cannot be private storage');
    $GLOBALS['fake_settings']=['EC_RELEASE_VERSION'=>'0.1.4','EC_TEST_UNSUPPORTED'=>'synthetic'];
    putenv('EC_RELEASE_VERSION');
    gate_assert(EC_Access::setting('EC_RELEASE_VERSION')==='0.1.4', 'administrator-saved release settings supported');
    gate_assert(EC_Access::setting('EC_TEST_UNSUPPORTED')==='', 'unsupported settings cannot be loaded from options');
} finally {
    foreach ($saved as $key=>$value) putenv($value===false ? $key : $key.'='.$value);
    unlink(EC_INSTALLER_PATH); rmdir($root.'/private'); rmdir($root.'/public'); rmdir($root);
}
