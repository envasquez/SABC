/**
 * Photo gallery page JavaScript functionality
 * Handles the lightbox modal and photo-delete confirmation.
 * Uses event delegation so HTMX-inserted photo cards are covered too.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const lightboxEl = document.getElementById('lightboxModal');
        const lightboxImage = document.getElementById('lightboxImage');
        const lightboxCaption = document.getElementById('lightboxCaption');
        const modal = lightboxEl ? new bootstrap.Modal(lightboxEl) : null;

        // Delegated click handler for opening the lightbox
        document.addEventListener('click', function(e) {
            const link = e.target.closest('.gallery-link');
            if (link && modal) {
                e.preventDefault();
                lightboxImage.src = link.href;
                lightboxCaption.textContent = link.dataset.caption || '';
                modal.show();
            }
        });

        // Delegated submit handler: confirm before deleting a photo
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.matches('.js-photo-delete-form')) {
                if (!confirm('Are you sure you want to delete this photo?')) {
                    e.preventDefault();
                }
            }
        });
    });
})();
