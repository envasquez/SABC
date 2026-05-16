/**
 * Admin Edit Poll page JavaScript functionality
 * Initializes edit poll form functionality
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        // Initialize remove button states.
        // Add-option behavior (including the hidden option_ids[] field for edit mode)
        // is driven by the .js-add-option button's data-include-hidden-id attribute,
        // handled by the delegated listener in poll-management.js.
        updateRemoveButtons();
    });
})();
