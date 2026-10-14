<?php
/** EmailChronicle presentation integration. Access controls live in a separate plugin. */
if (!defined('ABSPATH')) exit;
function dascalasu_ai_emailchronicle_assets() {
    if (is_page_template('page-emailchronicle.php') || is_page('emailchronicle')) {
        $path=get_template_directory().'/assets/css/emailchronicle.css';
        wp_enqueue_style('emailchronicle-portal',get_template_directory_uri().'/assets/css/emailchronicle.css',['dascalasu-ai-editorial'],(string)filemtime($path));
    }
}
add_action('wp_enqueue_scripts','dascalasu_ai_emailchronicle_assets');

// Keep one canonical project page; the build record supplies the existing project listing.
add_action('template_redirect', function() {
    if (is_singular('build') && get_post_field('post_name', get_queried_object_id()) === 'emailchronicle') {
        $page=get_page_by_path('emailchronicle', OBJECT, 'page');
        if ($page) { wp_safe_redirect(get_permalink($page), 301); exit; }
    }
});
