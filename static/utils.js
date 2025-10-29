/**
 * SABC Shared Utilities
 * Common functions used across the application
 */

/**
 * Escape HTML to prevent XSS attacks
 * Converts special characters to HTML entities
 *
 * @param {string} text - Text to escape
 * @returns {string} HTML-escaped text
 *
 * @example
 * escapeHtml('<script>alert("xss")</script>')
 * // Returns: '&lt;script&gt;alert("xss")&lt;/script&gt;'
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get CSRF token from cookie
 * Extracts the CSRF token needed for state-changing requests
 *
 * @returns {string|undefined} CSRF token or undefined if not found
 *
 * @example
 * const token = getCsrfToken();
 * fetch('/api/endpoint', {
 *     headers: { 'x-csrf-token': token }
 * });
 */
function getCsrfToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
}

/**
 * Show toast notification
 * Displays a Bootstrap toast notification to the user
 *
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in ms (default: 5000)
 *
 * @example
 * showToast('Operation completed successfully', 'success');
 * showToast('An error occurred', 'error', 3000);
 */
function showToast(message, type = 'info', duration = 5000) {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    // Map 'error' type to Bootstrap 'danger' class
    const bootstrapType = type === 'error' ? 'danger' : type;

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${bootstrapType} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${escapeHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();

    // Remove from DOM after hidden
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

/**
 * Create toast container if it doesn't exist
 * Internal helper function for showToast
 *
 * @returns {HTMLElement} Toast container element
 * @private
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

/**
 * Async DELETE request with CSRF token
 * Convenience function for making DELETE requests with proper CSRF protection
 *
 * @param {string} url - URL to send DELETE request to
 * @returns {Promise<Response>} Fetch response
 *
 * @example
 * const response = await deleteRequest('/admin/events/123');
 * if (response.ok) {
 *     showToast('Deleted successfully', 'success');
 * }
 */
async function deleteRequest(url) {
    return fetch(url, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'x-csrf-token': getCsrfToken(),
        }
    });
}

/**
 * Handle API errors consistently
 * Displays appropriate error messages from API responses
 *
 * @param {Response} response - Fetch response
 * @param {string} defaultMessage - Default error message if response has no error details
 * @throws {Error} Always throws after displaying error message
 *
 * @example
 * const response = await fetch('/api/endpoint');
 * await handleApiError(response, 'Failed to load data');
 */
async function handleApiError(response, defaultMessage = 'An error occurred') {
    if (!response.ok) {
        try {
            const data = await response.json();
            showToast(data.error || defaultMessage, 'error');
        } catch {
            showToast(`${defaultMessage} (status: ${response.status})`, 'error');
        }
        throw new Error(`API error: ${response.status}`);
    }
}
