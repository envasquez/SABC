/**
 * SABC Utility Functions
 * Common JavaScript utilities used across the application
 */

/**
 * Format a date for datetime-local input
 * @param {Date|string} date - The date to format
 * @returns {string} Formatted date string (YYYY-MM-DDTHH:MM)
 */
function formatDateTimeLocal(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Format a date for date input
 * @param {Date|string} date - The date to format
 * @returns {string} Formatted date string (YYYY-MM-DD)
 */
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Show a Bootstrap modal
 * @param {string} modalId - ID of the modal to show
 */
function showModal(modalId) {
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

/**
 * Hide a Bootstrap modal
 * @param {string} modalId - ID of the modal to hide
 */
function hideModal(modalId) {
    const modalElement = document.getElementById(modalId);
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    }
}

/**
 * Enable/disable a button
 * @param {string} buttonId - ID of the button
 * @param {boolean} enabled - Whether to enable the button
 */
function setButtonEnabled(buttonId, enabled) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = !enabled;
    }
}

/**
 * Show/hide an element
 * @param {string} elementId - ID of the element
 * @param {boolean} visible - Whether to show the element
 */
function setVisible(elementId, visible) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = visible ? 'block' : 'none';
    }
}

/**
 * Debounce a function call
 * @param {Function} func - The function to debounce
 * @param {number} wait - Milliseconds to wait
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Parse query string from URL
 * @param {string} queryString - Query string (optional, defaults to window.location.search)
 * @returns {Object} Parsed parameters
 */
function parseQueryString(queryString = window.location.search) {
    const params = new URLSearchParams(queryString);
    const result = {};
    for (const [key, value] of params) {
        result[key] = value;
    }
    return result;
}

/**
 * Confirm deletion with typed confirmation
 * @param {string} inputId - ID of the confirmation input
 * @param {string} buttonId - ID of the confirm button
 * @param {string} requiredText - Text that must be typed (default: "DELETE")
 */
function setupDeleteConfirmation(inputId, buttonId, requiredText = 'DELETE') {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);

    if (input && button) {
        input.addEventListener('input', function() {
            button.disabled = this.value !== requiredText;
        });
    }
}
