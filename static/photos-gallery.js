/**
 * Photo gallery page JavaScript.
 *
 * Opens the lightbox modal when a photo thumbnail is clicked. Delete
 * confirmation is handled by the generic data-confirm helper in utils.js.
 * Uses event delegation so HTMX-inserted photo cards are covered too.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const lightboxEl = document.getElementById('lightboxModal');
        const lightboxImage = document.getElementById('lightboxImage');
        const lightboxCaption = document.getElementById('lightboxCaption');
        const modal = lightboxEl ? new bootstrap.Modal(lightboxEl) : null;
        if (!modal) return;

        document.addEventListener('click', function(e) {
            const link = e.target.closest('.gallery-link');
            if (link) {
                e.preventDefault();
                lightboxImage.src = link.href;
                lightboxCaption.textContent = link.dataset.caption || '';
                modal.show();
            }
        });
    });
})();
