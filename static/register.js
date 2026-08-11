/**
 * Registration form double-submit guard.
 *
 * Signup is rate limited to three attempts per hour, and the server spends
 * ~300ms hashing the password before the row lands. A double-clicked submit
 * button therefore fired two registrations that raced each other to the
 * anglers.email unique index — one succeeded, the other returned an error to
 * a user who was in fact registered. The server now resolves that collision
 * correctly; this prevents it from happening at all, and keeps an accidental
 * double-click from consuming a second hourly attempt.
 */

(function () {
    'use strict';

    function guard(form) {
        form.addEventListener('submit', function () {
            const button = form.querySelector('button[type="submit"]');
            if (!button) return;
            // Defer past this submit event: disabling the button synchronously
            // can cancel the submission in some browsers.
            window.setTimeout(function () {
                button.disabled = true;
                button.classList.add('btn-loading');
            }, 0);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.querySelector('form[action="/register"]');
        if (form) guard(form);
    });

    // Restoring from the back/forward cache replays the disabled button, which
    // would leave the form unsubmittable. Re-enable it on restore.
    window.addEventListener('pageshow', function (event) {
        if (!event.persisted) return;
        const button = document.querySelector('form[action="/register"] button[type="submit"]');
        if (button) {
            button.disabled = false;
            button.classList.remove('btn-loading');
        }
    });
})();
