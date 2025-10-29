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
