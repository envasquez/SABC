/**
 * Bridge Tabler's bundled Bootstrap JS onto the bare `bootstrap` global.
 *
 * Tabler bundles Bootstrap and exposes the API on `window.tabler` (or
 * `window.tabler.bootstrap`, depending on version). Page scripts in this
 * codebase use the canonical `new bootstrap.Modal(...)` / `bootstrap.Tooltip`
 * API, so this file aliases it BEFORE utils.js or any page-specific
 * extra_js block runs. Must load synchronously after tabler.min.js and
 * before utils.js — see templates/base.html.
 *
 * Lives in a static file (not inline in base.html) so CSP can keep
 * script-src locked down without `'unsafe-inline'`. Previously inline;
 * after the Phase-6 CSP tightening the inline tag was silently blocked
 * and every Bootstrap modal / toast / tooltip on the site silently
 * failed with "bootstrap is not defined".
 */

(function () {
    if (window.bootstrap) return;
    if (window.tabler) {
        window.bootstrap = window.tabler.bootstrap || window.tabler;
    }
})();
