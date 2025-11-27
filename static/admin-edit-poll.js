/**
 * Admin Edit Poll page JavaScript functionality
 * Initializes edit poll form functionality
 */

// Save reference to original addOption function (from poll-management.js)
let originalAddOption;

document.addEventListener('DOMContentLoaded', function() {
    // Save original addOption reference
    originalAddOption = window.addOption;

    // Override addOption to include hidden option_ids field for edit mode
    window.addOption = function() {
        originalAddOption('poll-options-container', true);
    };

    // Initialize remove button states
    updateRemoveButtons();
});
