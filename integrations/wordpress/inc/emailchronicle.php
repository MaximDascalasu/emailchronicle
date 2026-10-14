<?php
/** EmailChronicle download portal configuration. No evidence upload endpoints. */
if (!defined('ABSPATH')) { exit; }

function dascalasu_ai_emailchronicle_customizer($customizer) {
    $customizer->add_section('emailchronicle_release', array('title' => 'EmailChronicle downloads', 'priority' => 160, 'description' => 'Publish a tested installer and its SHA-256. Keep evidence on the desktop.'));
    $fields = array(
        'installer_url' => array('Installer HTTPS URL', 'url', 'dascalasu_ai_emailchronicle_https'),
        'version' => array('Installer version', 'text', 'sanitize_text_field'),
        'sha256' => array('Installer SHA-256 (64 hexadecimal characters)', 'text', 'dascalasu_ai_emailchronicle_hash'),
        'release_notes_url' => array('Release notes HTTPS URL', 'url', 'dascalasu_ai_emailchronicle_https'),
        'signing_status' => array('Verified signing status', 'select', 'dascalasu_ai_emailchronicle_signing'),
    );
    foreach ($fields as $key => $field) {
        $id = 'emailchronicle_' . $key;
        $customizer->add_setting($id, array('default' => $key === 'signing_status' ? 'unsigned' : '', 'sanitize_callback' => $field[2], 'capability' => 'edit_theme_options'));
        $args = array('label' => $field[0], 'section' => 'emailchronicle_release', 'type' => $field[1]);
        if ($key === 'signing_status') {
            $args['choices'] = array('unsigned' => 'Unsigned preview / verification pending', 'signed' => 'Production signature verified by publisher');
        }
        $customizer->add_control($id, $args);
    }
}
add_action('customize_register', 'dascalasu_ai_emailchronicle_customizer');

function dascalasu_ai_emailchronicle_https($value) {
    return esc_url_raw((string) $value, array('https'));
}
function dascalasu_ai_emailchronicle_hash($value) {
    $value = strtolower(trim((string) $value));
    return preg_match('/^[a-f0-9]{64}$/', $value) ? $value : '';
}
function dascalasu_ai_emailchronicle_signing($value) {
    return $value === 'signed' ? 'signed' : 'unsigned';
}
function dascalasu_ai_emailchronicle_assets() {
    if (is_page_template('page-emailchronicle.php') || is_page('emailchronicle')) {
        $path = get_template_directory() . '/assets/css/emailchronicle.css';
        wp_enqueue_style('emailchronicle-portal', get_template_directory_uri() . '/assets/css/emailchronicle.css', array('dascalasu-ai-editorial'), (string) filemtime($path));
    }
}
add_action('wp_enqueue_scripts', 'dascalasu_ai_emailchronicle_assets');
