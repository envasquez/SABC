/**
 * Pre-paint FOUC suppression for dismissed cancelled-tournament alerts.
 *
 * Loaded synchronously in <head> before any body markup. Reads the
 * localStorage `dismissedCancelledAlerts` list and emits a tiny CSS rule
 * for each dismissed event so the alert never paints. Kept in its own
 * file (rather than inline) so CSP can drop 'unsafe-inline' from script-src.
 */

(function () {
    try {
        var dismissed = JSON.parse(localStorage.getItem('dismissedCancelledAlerts') || '[]');
        if (!Array.isArray(dismissed) || dismissed.length === 0) return;

        var rules = [];
        for (var i = 0; i < dismissed.length; i++) {
            var id = parseInt(dismissed[i], 10);
            if (!isNaN(id) && id > 0) {
                rules.push('#cancelled-alert-' + id + '{display:none!important}');
            }
        }
        if (rules.length) {
            var s = document.createElement('style');
            s.textContent = rules.join('');
            document.head.appendChild(s);
        }
    } catch (e) {
        // Ignore malformed localStorage
    }
})();
