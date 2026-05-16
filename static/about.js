/**
 * About page JavaScript functionality
 * Handles Cloudflare Turnstile CAPTCHA callbacks and contact-form submit guard.
 */

(function() {
    'use strict';

    /**
     * Turnstile success: enable the submit button.
     * Called by the Turnstile widget by name (data-callback attribute).
     */
    function onTurnstileSuccess() {
        var btn = document.getElementById('contact-submit');
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = '';
            btn.style.cursor = '';
        }
        var msg = document.getElementById('turnstile-msg');
        if (msg) msg.style.display = 'none';
    }

    /**
     * Turnstile expired: re-disable the submit button.
     * Called by the Turnstile widget by name (data-expired-callback attribute).
     */
    function onTurnstileExpired() {
        var btn = document.getElementById('contact-submit');
        if (btn) {
            btn.disabled = true;
            btn.style.opacity = '.5';
            btn.style.cursor = 'not-allowed';
        }
    }

    /**
     * Turnstile error: treat as expired.
     * Called by the Turnstile widget by name (data-error-callback attribute).
     */
    function onTurnstileError() {
        onTurnstileExpired();
    }

    document.addEventListener('DOMContentLoaded', function() {
        var form = document.querySelector('form[action="/about/contact"]');
        if (form) {
            form.addEventListener('submit', function(e) {
                // Only enforce the CAPTCHA guard when Turnstile is present on the page
                if (!document.querySelector('.cf-turnstile')) return;
                var resp = document.querySelector('input[name="cf-turnstile-response"]');
                if (!resp || !resp.value) {
                    e.preventDefault();
                    var msg = document.getElementById('turnstile-msg');
                    if (msg) msg.style.display = 'block';
                }
            });
        }
    });

    // Turnstile invokes these by name on the global scope, so they must be exported.
    window.onTurnstileSuccess = onTurnstileSuccess;
    window.onTurnstileExpired = onTurnstileExpired;
    window.onTurnstileError = onTurnstileError;
})();
