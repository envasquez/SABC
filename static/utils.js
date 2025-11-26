/**
 * SABC Shared Utilities
 * Common functions used across the application
 */

/**
 * Check if browser supports required features
 * Shows warning banner for incompatible browsers
 * @returns {boolean} True if browser is compatible
 */
function checkBrowserCompatibility() {
    const required = {
        fetch: typeof fetch === 'function',
        promise: typeof Promise !== 'undefined',
        arrow: (() => true)() === true,
        classlist: 'classList' in document.createElement('div'),
        queryselector: 'querySelector' in document,
        localstorage: (function() {
            try {
                return 'localStorage' in window && window.localStorage !== null;
            } catch(e) {
                return false;
            }
        })()
    };

    const unsupported = Object.keys(required).filter(f => !required[f]);

    if (unsupported.length > 0) {
        console.error('Unsupported browser features:', unsupported);
        showBrowserWarning();
        return false;
    }

    return true;
}

/**
 * Show warning banner for incompatible browsers
 * @private
 */
function showBrowserWarning() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showBrowserWarning);
        return;
    }

    const banner = document.createElement('div');
    banner.className = 'alert alert-warning alert-dismissible position-fixed top-0 start-0 end-0 m-3';
    banner.style.zIndex = '9999';
    banner.innerHTML = `
        <strong><i class="bi bi-exclamation-triangle me-2"></i>Browser Update Recommended</strong>
        <p class="mb-0 small">Some features may not work properly. Please update your browser for the best experience.</p>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.insertBefore(banner, document.body.firstChild);
}

// Run compatibility check on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkBrowserCompatibility);
} else {
    checkBrowserCompatibility();
}

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
 * Format a date for datetime-local input fields
 * Converts a Date object or date string to the format required by HTML datetime-local inputs
 *
 * @param {Date|string} date - The date to format
 * @returns {string} Formatted date string (YYYY-MM-DDTHH:MM)
 *
 * @example
 * formatDateTimeLocal(new Date())
 * // Returns: '2024-01-15T14:30'
 *
 * formatDateTimeLocal('2024-01-15')
 * // Returns: '2024-01-15T00:00'
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
 * Fetch with automatic retry on failure
 * Handles network issues and temporary server errors gracefully
 *
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @param {number} retries - Maximum retry attempts (default: 3)
 * @returns {Promise<Response>} Fetch response
 *
 * @example
 * const response = await fetchWithRetry('/api/data', { method: 'GET' });
 * if (response.ok) {
 *     const data = await response.json();
 * }
 */
async function fetchWithRetry(url, options = {}, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);

            // Success - return immediately
            if (response.ok) return response;

            // Client errors (4xx) - don't retry
            if (response.status >= 400 && response.status < 500) {
                return response;
            }

            // Server errors (5xx) - retry
            if (i === retries - 1) {
                return response; // Last attempt, return error response
            }

            console.warn(`Request failed with status ${response.status}, retrying (${i + 1}/${retries})...`);
        } catch (error) {
            // Network error or timeout
            if (i === retries - 1) {
                console.error('Request failed after all retries:', error);
                throw error;
            }

            console.warn(`Network error, retrying (${i + 1}/${retries})...`, error.message);
        }

        // Wait before retry: 1s, 2s, 4s (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
    }
}

/**
 * Async DELETE request with CSRF token and retry logic
 * Convenience function for making DELETE requests with proper CSRF protection
 *
 * @param {string} url - URL to send DELETE request to
 * @param {number} retries - Maximum retry attempts (default: 3)
 * @returns {Promise<Response>} Fetch response
 *
 * @example
 * const response = await deleteRequest('/admin/events/123');
 * if (response.ok) {
 *     showToast('Deleted successfully', 'success');
 * }
 */
async function deleteRequest(url, retries = 3) {
    return fetchWithRetry(url, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'x-csrf-token': getCsrfToken(),
        }
    }, retries);
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

/**
 * LakeRampSelector - Reusable component for lake/ramp dropdown selection
 * Handles the common pattern of populating ramp dropdowns based on lake selection
 *
 * @class
 *
 * @example
 * // Using with API data (admin-events.js pattern)
 * const selector = new LakeRampSelector({
 *     lakeSelectId: 'lake_select',
 *     rampSelectId: 'ramp_select',
 *     lakesData: lakesData,  // Array format: [{key: 'travis', name: 'Lake Travis'}, ...]
 *     useApi: true
 * });
 * await selector.loadRampsForLake('Lake Travis');
 *
 * @example
 * // Using with pre-loaded data (polls.js pattern)
 * const selector = new LakeRampSelector({
 *     lakeSelectId: 'poll_lake',
 *     rampSelectId: 'poll_ramp',
 *     lakesData: lakesAndRamps,  // Object format: {1: {name: 'Lake Travis', ramps: [...]}, ...}
 *     useApi: false
 * });
 * selector.loadRampsForLakeId(1);
 */
class LakeRampSelector {
    /**
     * Create a LakeRampSelector instance
     * @param {Object} options - Configuration options
     * @param {string} options.lakeSelectId - ID of lake select element
     * @param {string} options.rampSelectId - ID of ramp select element
     * @param {Array|Object} options.lakesData - Lakes data (array or object format)
     * @param {boolean} [options.useApi=false] - Whether to fetch ramps via API
     * @param {string} [options.emptyText='-- Select Ramp --'] - Text for empty option
     */
    constructor({ lakeSelectId, rampSelectId, lakesData, useApi = false, emptyText = '-- Select Ramp --' }) {
        this.lakeSelectId = lakeSelectId;
        this.rampSelectId = rampSelectId;
        this.lakesData = lakesData;
        this.useApi = useApi;
        this.emptyText = emptyText;
    }

    /**
     * Get the lake select element
     * @returns {HTMLSelectElement|null}
     * @private
     */
    getLakeSelect() {
        return document.getElementById(this.lakeSelectId);
    }

    /**
     * Get the ramp select element
     * @returns {HTMLSelectElement|null}
     * @private
     */
    getRampSelect() {
        return document.getElementById(this.rampSelectId);
    }

    /**
     * Clear ramp dropdown and disable it
     * @private
     */
    clearRamps() {
        const rampSelect = this.getRampSelect();
        if (!rampSelect) return;

        rampSelect.innerHTML = `<option value="">${this.emptyText}</option>`;
        rampSelect.disabled = true;
    }

    /**
     * Populate ramp dropdown with options
     * @param {Array} ramps - Array of ramp objects
     * @param {string} [valueKey='id'] - Property to use for option value
     * @param {string} [textKey='name'] - Property to use for option text
     * @private
     */
    populateRamps(ramps, valueKey = 'id', textKey = 'name') {
        const rampSelect = this.getRampSelect();
        if (!rampSelect) return;

        rampSelect.innerHTML = `<option value="">${this.emptyText}</option>`;

        if (!ramps || ramps.length === 0) {
            rampSelect.disabled = true;
            return;
        }

        ramps.forEach(ramp => {
            const option = document.createElement('option');
            // Handle both string values and object values
            if (typeof ramp === 'string') {
                option.value = ramp;
                option.textContent = ramp;
            } else {
                option.value = ramp[valueKey];
                option.textContent = ramp[textKey];
            }
            rampSelect.appendChild(option);
        });

        rampSelect.disabled = false;
    }

    /**
     * Load ramps for a lake by name (admin-events.js pattern with API)
     * @param {string} lakeName - Name of the lake
     * @returns {Promise<void>}
     */
    async loadRampsForLake(lakeName) {
        if (!lakeName) {
            this.clearRamps();
            return;
        }

        // Find lake in lakesData array
        const lake = Array.isArray(this.lakesData)
            ? this.lakesData.find(l => l.name === lakeName)
            : null;

        if (!lake) {
            this.clearRamps();
            return;
        }

        if (this.useApi) {
            await this.fetchRampsFromApi(lake.key);
        } else {
            // If not using API, lakesData should have ramps embedded
            this.populateRamps(lake.ramps || [], 'name', 'name');
        }
    }

    /**
     * Load ramps for a lake by ID (polls.js pattern with pre-loaded data)
     * @param {number|string} lakeId - ID of the lake
     */
    loadRampsForLakeId(lakeId) {
        if (!lakeId) {
            this.clearRamps();
            return;
        }

        // Handle object format: {1: {name: 'Lake Travis', ramps: [...]}, ...}
        if (typeof this.lakesData === 'object' && !Array.isArray(this.lakesData)) {
            const lake = this.lakesData[lakeId];
            if (lake && lake.ramps) {
                this.populateRamps(lake.ramps, 'id', 'name');
            } else {
                this.clearRamps();
            }
        }
        // Handle array format: [{id: 1, name: 'Lake Travis', ramps: [...]}, ...]
        else if (Array.isArray(this.lakesData)) {
            const lake = this.lakesData.find(l => l.id == lakeId);
            if (lake && lake.ramps) {
                this.populateRamps(lake.ramps, 'id', 'name');
            } else {
                this.clearRamps();
            }
        }
    }

    /**
     * Fetch ramps from API endpoint
     * @param {string} lakeKey - Lake key for API endpoint
     * @returns {Promise<void>}
     * @private
     */
    async fetchRampsFromApi(lakeKey) {
        const rampSelect = this.getRampSelect();
        if (!rampSelect) return;

        try {
            const response = await fetch(`/api/lakes/${lakeKey}/ramps`);
            const data = await response.json();

            this.populateRamps(data.ramps || [], 'name', 'name');
        } catch (error) {
            console.error(`Error loading ramps for ${lakeKey}:`, error);
            rampSelect.innerHTML = `<option value="">-- Error loading ramps --</option>`;
            rampSelect.disabled = true;
        }
    }

    /**
     * Set the selected ramp value
     * @param {string|number} rampValue - Value to select
     */
    setRampValue(rampValue) {
        const rampSelect = this.getRampSelect();
        if (rampSelect && rampValue) {
            rampSelect.value = rampValue;
        }
    }

    /**
     * Set up auto-wiring for lake select change event
     * Automatically loads ramps when lake selection changes
     * @param {boolean} [useId=false] - Whether to use lake ID (true) or name (false)
     */
    autoWire(useId = false) {
        const lakeSelect = this.getLakeSelect();
        if (!lakeSelect) return;

        lakeSelect.addEventListener('change', async () => {
            const value = lakeSelect.value;
            if (useId) {
                this.loadRampsForLakeId(value);
            } else {
                await this.loadRampsForLake(value);
            }
        });
    }
}

/**
 * Show a Bootstrap modal
 * Convenience function for displaying modals
 *
 * @param {string} modalId - ID of the modal element (without #)
 *
 * @example
 * showModal('deleteConfirmModal');
 */
function showModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (!modalElement) {
        console.error(`Modal with ID '${modalId}' not found`);
        return;
    }
    new bootstrap.Modal(modalElement).show();
}

/**
 * Hide a Bootstrap modal
 * Convenience function for hiding modals
 *
 * @param {string} modalId - ID of the modal element (without #)
 *
 * @example
 * hideModal('deleteConfirmModal');
 */
function hideModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (!modalElement) {
        console.error(`Modal with ID '${modalId}' not found`);
        return;
    }
    const modalInstance = bootstrap.Modal.getInstance(modalElement);
    if (modalInstance) {
        modalInstance.hide();
    }
}

/**
 * DeleteConfirmationManager - Reusable component for delete confirmation workflows
 * Handles the common pattern of: show modal → require "DELETE" confirmation → execute delete
 *
 * @class
 *
 * @example
 * const deleteManager = new DeleteConfirmationManager({
 *     modalId: 'deleteUserModal',
 *     itemNameElementId: 'deleteUserName',
 *     confirmInputId: 'deleteConfirmInput',
 *     confirmButtonId: 'confirmDeleteBtn',
 *     deleteUrlTemplate: (id) => `/admin/users/${id}`,
 *     onSuccess: () => location.reload(),
 *     onError: (error) => showToast(`Failed to delete: ${error}`, 'error')
 * });
 *
 * // Show confirmation modal
 * deleteManager.confirm(123, 'John Doe');
 */
class DeleteConfirmationManager {
    /**
     * Create a DeleteConfirmationManager instance
     * @param {Object} options - Configuration options
     * @param {string} options.modalId - ID of the modal element
     * @param {string} options.itemNameElementId - ID of element to display item name
     * @param {string} options.confirmInputId - ID of confirmation input field
     * @param {string} options.confirmButtonId - ID of confirm delete button
     * @param {Function} options.deleteUrlTemplate - Function that takes ID and returns delete URL
     * @param {Function} [options.onSuccess] - Callback after successful delete
     * @param {Function} [options.onError] - Callback after failed delete
     * @param {string} [options.confirmText='DELETE'] - Required confirmation text
     */
    constructor({
        modalId,
        itemNameElementId,
        confirmInputId,
        confirmButtonId,
        deleteUrlTemplate,
        onSuccess = () => location.reload(),
        onError = (error) => showToast(`Delete failed: ${error}`, 'error'),
        confirmText = 'DELETE'
    }) {
        this.modalId = modalId;
        this.itemNameElementId = itemNameElementId;
        this.confirmInputId = confirmInputId;
        this.confirmButtonId = confirmButtonId;
        this.deleteUrlTemplate = deleteUrlTemplate;
        this.onSuccess = onSuccess;
        this.onError = onError;
        this.confirmText = confirmText;
        this.itemId = null;

        this.setupEventListeners();
    }

    /**
     * Set up event listeners for confirmation input and button
     * @private
     */
    setupEventListeners() {
        // Enable/disable button based on confirmation text
        const confirmInput = document.getElementById(this.confirmInputId);
        if (confirmInput) {
            confirmInput.addEventListener('input', (e) => {
                const btn = document.getElementById(this.confirmButtonId);
                if (btn) {
                    btn.disabled = e.target.value !== this.confirmText;
                }
            });
        }

        // Handle delete button click
        const confirmButton = document.getElementById(this.confirmButtonId);
        if (confirmButton) {
            confirmButton.addEventListener('click', () => this.executeDelete());
        }
    }

    /**
     * Show confirmation modal for deleting an item
     * @param {number|string} itemId - ID of the item to delete
     * @param {string} itemName - Name/description of item (shown in modal)
     */
    confirm(itemId, itemName) {
        this.itemId = itemId;

        // Set item name in modal
        const itemNameElement = document.getElementById(this.itemNameElementId);
        if (itemNameElement) {
            itemNameElement.textContent = itemName;
        }

        // Clear confirmation input
        const confirmInput = document.getElementById(this.confirmInputId);
        if (confirmInput) {
            confirmInput.value = '';
        }

        // Disable confirm button
        const confirmButton = document.getElementById(this.confirmButtonId);
        if (confirmButton) {
            confirmButton.disabled = true;
        }

        // Show modal
        showModal(this.modalId);
    }

    /**
     * Execute the delete operation
     * @private
     */
    async executeDelete() {
        if (!this.itemId) {
            console.error('No item ID set for deletion');
            return;
        }

        // Verify confirmation text
        const confirmInput = document.getElementById(this.confirmInputId);
        if (confirmInput && confirmInput.value !== this.confirmText) {
            showToast(`Please type ${this.confirmText} to confirm`, 'warning');
            return;
        }

        // Close the modal
        hideModal(this.modalId);

        // Execute DELETE request
        try {
            const url = this.deleteUrlTemplate(this.itemId);
            const response = await deleteRequest(url);

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                this.onSuccess(data);
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            this.onError(error.message);
        }
    }
}
