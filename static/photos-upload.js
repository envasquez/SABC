/**
 * Photo upload page JavaScript functionality
 * Handles client-side image preview and submit-button state.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const photoInput = document.getElementById('photo');
        const preview = document.getElementById('preview');
        const previewPlaceholder = document.getElementById('previewPlaceholder');
        const submitBtn = document.getElementById('submitBtn');
        const form = document.getElementById('uploadForm');

        if (photoInput) {
            photoInput.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    if (file.size > 10 * 1024 * 1024) {
                        alert('File is too large. Maximum size is 10MB.');
                        this.value = '';
                        return;
                    }
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                        previewPlaceholder.style.display = 'none';
                    };
                    reader.readAsDataURL(file);
                } else {
                    preview.style.display = 'none';
                    previewPlaceholder.style.display = 'block';
                }
            });
        }

        if (form && submitBtn) {
            form.addEventListener('submit', function() {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" style="margin-right:.25rem"></span> Uploading...';
            });
        }
    });
})();
