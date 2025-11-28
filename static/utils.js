/**
 * SABC Shared Utilities
 * Common functions used across the application
 */

// ============================================================================
// CHART STYLING UTILITIES
// Beautiful, modern chart styling with gradients, shadows, and animations
// ============================================================================

/**
 * Outdoor/fishing-themed color palette
 * Deep blues, teals, and earth tones inspired by lakes and nature
 */
const CHART_COLORS = {
    // Primary palette - water/nature inspired
    palette: [
        { base: '#0077B6', light: '#00B4D8', name: 'Ocean Blue' },
        { base: '#2A9D8F', light: '#40C9A2', name: 'Teal' },
        { base: '#E76F51', light: '#F4A261', name: 'Sunset Orange' },
        { base: '#264653', light: '#3D5A6C', name: 'Deep Sea' },
        { base: '#8338EC', light: '#A855F7', name: 'Purple' },
        { base: '#06D6A0', light: '#34D399', name: 'Emerald' },
        { base: '#EF476F', light: '#F472B6', name: 'Coral' },
        { base: '#118AB2', light: '#38BDF8', name: 'Sky Blue' },
        { base: '#FFD166', light: '#FDE68A', name: 'Gold' },
        { base: '#073B4C', light: '#1E5A6E', name: 'Midnight' }
    ],
    // Get color at index with fallback
    get: function(index) {
        return this.palette[index % this.palette.length];
    }
};

/**
 * Create a horizontal gradient for chart bars
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {Object} chartArea - Chart area dimensions
 * @param {string} colorStart - Start color (left)
 * @param {string} colorEnd - End color (right)
 * @returns {CanvasGradient} Gradient object
 */
function createBarGradient(ctx, chartArea, colorStart, colorEnd) {
    const gradient = ctx.createLinearGradient(
        chartArea.left, 0,
        chartArea.right, 0
    );
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
}

/**
 * Shared Chart.js configuration for beautiful charts
 */
const CHART_CONFIG = {
    // Animation settings
    animation: {
        duration: 800,
        easing: 'easeOutQuart',
        delay: function(context) {
            // Stagger animation by bar index
            return context.dataIndex * 100;
        }
    },

    // Common tooltip styling
    tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        titleColor: '#fff',
        bodyColor: '#e2e8f0',
        titleFont: { size: 14, weight: 'bold' },
        bodyFont: { size: 13 },
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
        boxPadding: 6,
        caretSize: 8,
        caretPadding: 10
    },

    // Common scale styling (designed for dark backgrounds)
    scales: {
        x: {
            grid: {
                display: true,
                color: 'rgba(148, 163, 184, 0.15)',
                drawBorder: false
            },
            ticks: {
                font: { size: 11, weight: '500' },
                color: '#94a3b8'  // Light gray for dark backgrounds
            }
        },
        y: {
            grid: {
                display: false,
                drawBorder: false
            },
            ticks: {
                font: { size: 13, weight: '600' },
                color: '#e2e8f0'  // Light text for dark backgrounds
            }
        }
    },

    // Bar styling
    bar: {
        borderRadius: 6,
        borderSkipped: false,
        barThickness: 28,
        maxBarThickness: 35
    }
};

/**
 * Custom Chart.js plugin for drawing vote labels on bars
 */
const voteLabelsPlugin = {
    id: 'voteLabels',
    afterDatasetsDraw: function(chart, args, options) {
        if (!options.enabled) return;

        const ctx = chart.ctx;
        const meta = chart.getDatasetMeta(0);

        ctx.save();
        ctx.font = 'bold 12px system-ui, -apple-system, sans-serif';
        ctx.textBaseline = 'middle';

        meta.data.forEach((bar, index) => {
            const data = options.data[index];
            if (!data || data.votes === 0) return;

            const votes = data.votes;
            const percentage = options.totalVotes > 0
                ? Math.round((votes / options.totalVotes) * 100)
                : 0;

            const text = votes + ' (' + percentage + '%)';
            const textWidth = ctx.measureText(text).width;

            // Position: inside bar if fits, otherwise outside
            const barWidth = bar.width;
            const insideBar = barWidth > textWidth + 20;

            if (insideBar) {
                ctx.textAlign = 'right';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
                ctx.fillText(text, bar.x - 8, bar.y);
            } else {
                ctx.textAlign = 'left';
                ctx.fillStyle = '#e2e8f0';  // Light color for dark backgrounds
                ctx.fillText(text, bar.x + 8, bar.y);
            }
        });

        ctx.restore();
    }
};

/**
 * Custom Chart.js plugin for drawing total vote labels on stacked bar charts
 * Shows the total votes for each bar (sum of all segments) at the end
 */
const stackedTotalsPlugin = {
    id: 'stackedTotals',
    afterDatasetsDraw: function(chart, args, options) {
        if (!options.enabled) return;

        const ctx = chart.ctx;
        const datasets = chart.data.datasets;
        const meta = chart.getDatasetMeta(datasets.length - 1);  // Use last dataset for bar positions

        ctx.save();
        ctx.font = 'bold 12px system-ui, -apple-system, sans-serif';
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'left';
        ctx.fillStyle = '#e2e8f0';  // Light color for dark backgrounds

        // Calculate totals for each bar (each lake)
        const barTotals = [];
        const numBars = datasets[0]?.data?.length || 0;
        for (let i = 0; i < numBars; i++) {
            let total = 0;
            datasets.forEach(ds => {
                total += ds.data[i] || 0;
            });
            barTotals.push(total);
        }

        // Draw total at the end of each stacked bar
        meta.data.forEach((bar, index) => {
            const total = barTotals[index];
            if (total === 0) return;

            const percentage = options.totalVotes > 0
                ? Math.round((total / options.totalVotes) * 100)
                : 0;

            const text = total + ' (' + percentage + '%)';
            ctx.fillText(text, bar.x + 8, bar.y);
        });

        ctx.restore();
    }
};

// Register the plugins globally
if (typeof Chart !== 'undefined') {
    Chart.register(voteLabelsPlugin);
    Chart.register(stackedTotalsPlugin);
}

// ============================================================================
// END CHART STYLING UTILITIES
// ============================================================================

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
/**
 * Format 24-hour time to 12-hour format with AM/PM
 * Converts time strings like "14:30" to "2:30 PM"
 *
 * @param {string} time24 - Time in 24-hour format (HH:MM)
 * @returns {string} Time in 12-hour format (H:MM AM/PM)
 *
 * @example
 * formatTime12Hour('14:30')
 * // Returns: '2:30 PM'
 *
 * formatTime12Hour('09:00')
 * // Returns: '9:00 AM'
 */
function formatTime12Hour(time24) {
    if (!time24) return '';
    const parts = time24.split(':');
    const hour = parseInt(parts[0]);
    const minutes = parts[1];
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return hour12 + ':' + minutes + ' ' + ampm;
}

/**
 * Get lake name by ID from lakes data array
 * Used for poll result visualization to display lake names
 *
 * @param {Array} lakesData - Array of lake objects with id, name, and ramps
 * @param {number|string} lakeId - Lake ID to find
 * @returns {string} Lake name or fallback "Lake {id}"
 *
 * @example
 * const lakes = [{id: 1, name: 'Lake Travis', ramps: [...]}, ...];
 * getLakeName(lakes, 1)
 * // Returns: 'Lake Travis'
 */
function getLakeName(lakesData, lakeId) {
    if (!lakeId) return 'Unknown Lake';
    if (lakesData && Array.isArray(lakesData)) {
        const lake = lakesData.find(function(l) { return l.id == lakeId; });
        if (lake) return lake.name;
    }
    return 'Lake ' + lakeId;
}

/**
 * Get ramp name by ID from lakes data array
 * Searches through all lakes to find the ramp with matching ID
 *
 * @param {Array} lakesData - Array of lake objects with id, name, and ramps
 * @param {number|string} rampId - Ramp ID to find
 * @returns {string} Ramp name or fallback "Ramp {id}"
 *
 * @example
 * const lakes = [{id: 1, name: 'Lake Travis', ramps: [{id: 10, name: 'Mansfield Dam'}]}, ...];
 * getRampName(lakes, 10)
 * // Returns: 'Mansfield Dam'
 */
function getRampName(lakesData, rampId) {
    if (!rampId) return 'Unknown Ramp';
    if (lakesData && Array.isArray(lakesData)) {
        for (let i = 0; i < lakesData.length; i++) {
            const ramp = lakesData[i].ramps.find(function(r) { return r.id == rampId; });
            if (ramp) return ramp.name;
        }
    }
    return 'Ramp ' + rampId;
}

/**
 * PollResultsRenderer - Reusable component for rendering poll results visualization
 * Handles aggregating votes and rendering lakes with stacked ramp bars and times tables
 *
 * @class
 *
 * @example
 * const renderer = new PollResultsRenderer({
 *     lakesData: lakesData,
 *     containerSelector: '.tournament-results-container',
 *     idAttribute: 'pollId',  // data-poll-id attribute
 *     onLakeSelect: (id, lakeId) => console.log('Lake selected:', lakeId)
 * });
 * renderer.renderAll();
 */
class PollResultsRenderer {
    /**
     * Create a PollResultsRenderer instance
     * @param {Object} options - Configuration options
     * @param {Array} options.lakesData - Array of lake objects with id, name, and ramps
     * @param {string} options.containerSelector - CSS selector for result containers
     * @param {string} [options.idAttribute='pollId'] - Data attribute name for poll/tournament ID
     * @param {Function} [options.onLakeSelect] - Callback when lake is selected
     */
    constructor({ lakesData, containerSelector, idAttribute = 'pollId', onLakeSelect = null }) {
        this.lakesData = lakesData || [];
        this.containerSelector = containerSelector;
        this.idAttribute = idAttribute;
        this.onLakeSelect = onLakeSelect;
        this.resultsData = {};  // Store aggregated data by ID
        this.charts = {};  // Store Chart.js instances for cleanup

        // Use shared color palette
        this.colors = CHART_COLORS;
    }

    /**
     * Get lake name using instance's lakesData
     * @param {number|string} lakeId - Lake ID
     * @returns {string} Lake name
     */
    getLakeName(lakeId) {
        return getLakeName(this.lakesData, lakeId);
    }

    /**
     * Get ramp name using instance's lakesData
     * @param {number|string} rampId - Ramp ID
     * @returns {string} Ramp name
     */
    getRampName(rampId) {
        return getRampName(this.lakesData, rampId);
    }

    /**
     * Aggregate votes from poll option data elements
     * Groups ramps by lake for stacked bar visualization
     * @param {HTMLElement} container - Container element with poll option data
     * @returns {Object} Aggregated data with lakes, ramps, rampsByLake, and times
     */
    aggregateVotes(container) {
        const optionElements = container.querySelectorAll('.poll-option-data');
        const lakes = {};
        const ramps = {};
        const rampsByLake = {};  // For stacked bar chart
        const times = {};

        optionElements.forEach(el => {
            let optionData = {};
            try {
                optionData = el.dataset.optionData ? JSON.parse(el.dataset.optionData) : {};
            } catch (e) {
                console.error('[SABC] Error parsing option data:', e);
            }
            const voteCount = parseInt(el.dataset.voteCount) || 0;

            if (voteCount === 0) return;

            const lakeId = optionData.lake_id;
            const rampId = optionData.ramp_id;
            const startTime = optionData.start_time;
            const endTime = optionData.end_time;

            // Aggregate lake votes
            if (lakeId) {
                if (!lakes[lakeId]) {
                    lakes[lakeId] = { id: lakeId, name: this.getLakeName(lakeId), votes: 0 };
                }
                lakes[lakeId].votes += voteCount;

                // Initialize rampsByLake for this lake
                if (!rampsByLake[lakeId]) {
                    rampsByLake[lakeId] = {};
                }
            }

            // Aggregate ramp votes (grouped by lake)
            if (rampId && lakeId) {
                if (!ramps[rampId]) {
                    ramps[rampId] = { id: rampId, lake_id: lakeId, name: this.getRampName(rampId), votes: 0 };
                }
                ramps[rampId].votes += voteCount;

                // Add to rampsByLake for stacked bar
                if (!rampsByLake[lakeId][rampId]) {
                    rampsByLake[lakeId][rampId] = {
                        id: rampId,
                        name: this.getRampName(rampId),
                        votes: 0
                    };
                }
                rampsByLake[lakeId][rampId].votes += voteCount;
            }

            // Aggregate time votes
            if (startTime && endTime) {
                const timeKey = startTime + '-' + endTime;
                if (!times[timeKey]) {
                    times[timeKey] = { start_time: startTime, end_time: endTime, votes: 0 };
                }
                times[timeKey].votes += voteCount;
            }
        });

        // Sort by votes (descending)
        return {
            lakes: Object.values(lakes).sort((a, b) => b.votes - a.votes),
            ramps: Object.values(ramps).sort((a, b) => b.votes - a.votes),
            rampsByLake: rampsByLake,
            times: Object.values(times).sort((a, b) => b.votes - a.votes)
        };
    }

    /**
     * Build unique ramp list across all lakes for consistent coloring
     * Uses gradient colors from the shared palette
     * @param {Object} rampsByLake - Ramps grouped by lake ID
     * @returns {Array} Array of unique ramp objects with assigned colors
     */
    buildRampColorMap(rampsByLake) {
        const uniqueRamps = {};
        Object.values(rampsByLake).forEach(lakeRamps => {
            Object.values(lakeRamps).forEach(ramp => {
                if (!uniqueRamps[ramp.id]) {
                    uniqueRamps[ramp.id] = {
                        id: ramp.id,
                        name: ramp.name
                    };
                }
            });
        });

        // Sort by name for consistent ordering
        const sortedRamps = Object.values(uniqueRamps).sort((a, b) =>
            a.name.localeCompare(b.name)
        );

        // Assign colors from the beautiful palette
        sortedRamps.forEach((ramp, index) => {
            const colorSet = this.colors.get(index);
            ramp.baseColor = colorSet.base;
            ramp.lightColor = colorSet.light;
        });

        return sortedRamps;
    }

    /**
     * Draw beautiful stacked bar chart using Chart.js
     * Features: gradients, rounded corners, smooth animations, styled tooltips
     * @param {string|number} id - Poll/tournament ID
     * @param {Array} lakesArray - Array of lake vote data
     * @param {Object} rampsByLake - Ramps grouped by lake ID
     */
    drawStackedBarChart(id, lakesArray, rampsByLake) {
        const canvasContainer = document.getElementById('stackedChart-' + id);
        if (!canvasContainer) return;

        // Destroy existing chart if any
        if (this.charts[id]) {
            this.charts[id].destroy();
        }

        if (!lakesArray || lakesArray.length === 0) {
            canvasContainer.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox text-muted" style="font-size: 2.5rem; opacity: 0.5;"></i>
                    <p class="text-muted mt-2 mb-0">No votes yet</p>
                </div>`;
            return;
        }

        // Build color map for ramps
        const rampColorMap = this.buildRampColorMap(rampsByLake);

        // Calculate total votes per ramp for legend display
        const rampTotals = {};
        Object.values(rampsByLake).forEach(lakeRamps => {
            Object.values(lakeRamps).forEach(ramp => {
                rampTotals[ramp.id] = (rampTotals[ramp.id] || 0) + ramp.votes;
            });
        });

        // Create container with canvas and custom legend
        canvasContainer.innerHTML = `
            <canvas id="chartCanvas-${id}"></canvas>
            <div id="chartLegend-${id}" class="chart-legend-pills"></div>
        `;
        const canvas = document.getElementById('chartCanvas-' + id);
        const ctx = canvas.getContext('2d');
        const legendContainer = document.getElementById('chartLegend-' + id);

        // Build custom pill legend - only show ramps with votes
        const activeRamps = rampColorMap.filter(ramp => rampTotals[ramp.id] > 0);
        legendContainer.innerHTML = activeRamps.map(ramp => {
            const votes = rampTotals[ramp.id] || 0;
            return `<span class="legend-pill" style="background: ${ramp.baseColor};">
                <span class="legend-pill-name">${ramp.name}</span>
                <span class="legend-pill-votes">${votes}</span>
            </span>`;
        }).join('');

        // Prepare data for Chart.js stacked bar
        const labels = lakesArray.map(lake => lake.name);

        // Create datasets with gradient colors - one per unique ramp
        const datasets = rampColorMap.map((ramp) => {
            const data = lakesArray.map(lake => {
                const lakeRamps = rampsByLake[lake.id] || {};
                const rampData = lakeRamps[ramp.id];
                return rampData ? rampData.votes : 0;
            });

            return {
                label: ramp.name,
                data: data,
                backgroundColor: ramp.baseColor,
                hoverBackgroundColor: ramp.lightColor,
                borderColor: 'rgba(255, 255, 255, 0.3)',
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            };
        });

        // Filter out datasets with all zeros
        const activeDatasets = datasets.filter(ds =>
            ds.data.some(v => v > 0)
        );

        // Calculate total votes for percentage display
        let totalVotes = 0;
        lakesArray.forEach(lake => {
            const lakeRamps = rampsByLake[lake.id] || {};
            Object.values(lakeRamps).forEach(ramp => {
                totalVotes += ramp.votes;
            });
        });

        // Calculate dynamic height based on number of lakes (no legend height needed - using custom legend)
        const barHeight = 55;
        const minHeight = 180;
        const calculatedHeight = Math.max(minHeight, lakesArray.length * barHeight + 40);
        canvas.style.height = calculatedHeight + 'px';

        // Create the chart with beautiful styling
        this.charts[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: activeDatasets
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: { right: 70, left: 5, top: 10, bottom: 10 }  // Extra right padding for vote labels
                },
                plugins: {
                    legend: {
                        display: false  // Using custom HTML pill legend instead
                    },
                    tooltip: {
                        ...CHART_CONFIG.tooltip,
                        mode: 'point',
                        callbacks: {
                            title: function(context) {
                                return '📍 ' + context[0].label;
                            },
                            label: function(context) {
                                const rampName = context.dataset.label;
                                const votes = context.raw;
                                if (votes === 0) return null;
                                const pct = totalVotes > 0 ? Math.round((votes / totalVotes) * 100) : 0;
                                return rampName + ': ' + votes + ' vote' + (votes !== 1 ? 's' : '') + ' (' + pct + '%)';
                            },
                            afterBody: function(context) {
                                const lakeIndex = context[0].dataIndex;
                                let lakeTotal = 0;
                                activeDatasets.forEach(ds => {
                                    lakeTotal += ds.data[lakeIndex];
                                });
                                const lakePct = totalVotes > 0 ? Math.round((lakeTotal / totalVotes) * 100) : 0;
                                return '\n━━━━━━━━━━━━━━━\nLake Total: ' + lakeTotal + ' votes (' + lakePct + '%)';
                            }
                        }
                    },
                    // Show total vote counts at end of stacked bars
                    stackedTotals: {
                        enabled: true,
                        totalVotes: totalVotes
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        beginAtZero: true,
                        ...CHART_CONFIG.scales.x,
                        ticks: {
                            ...CHART_CONFIG.scales.x.ticks,
                            stepSize: 1
                        },
                        title: {
                            display: true,
                            text: 'Votes',
                            font: { size: 12, weight: '600' },
                            color: '#94a3b8',
                            padding: { top: 10 }
                        }
                    },
                    y: {
                        stacked: true,
                        ...CHART_CONFIG.scales.y,
                        ticks: {
                            ...CHART_CONFIG.scales.y.ticks,
                            padding: 8
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'y',
                    intersect: false
                },
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                // Hover effects
                onHover: function(event, elements) {
                    event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
                }
            }
        });
    }

    /**
     * Draw times table
     * @param {string|number} id - Poll/tournament ID
     * @param {Array} timesArray - Array of time vote data
     */
    drawTimesTable(id, timesArray) {
        const tableBody = document.querySelector('#timeTable-' + id + ' tbody');
        if (!tableBody) return;

        if (!timesArray || timesArray.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-secondary text-center py-3"><i class="bi bi-inbox me-2"></i>No votes</td></tr>';
            return;
        }

        tableBody.innerHTML = timesArray.map(time => {
            return '<tr>' +
                '<td class="small">' + formatTime12Hour(time.start_time) + '</td>' +
                '<td class="small">' + formatTime12Hour(time.end_time) + '</td>' +
                '<td class="small text-center"><span class="badge bg-primary">' + time.votes + '</span></td>' +
            '</tr>';
        }).join('');
    }

    /**
     * Render results for a single container
     * @param {HTMLElement} container - Container element
     */
    renderContainer(container) {
        const id = container.dataset[this.idAttribute];
        if (!id) return;

        // Aggregate votes
        const resultsData = this.aggregateVotes(container);
        this.resultsData[id] = resultsData;

        // Also store globally for backward compatibility
        window['pollResultsData_' + id] = resultsData;

        // Render stacked bar chart (lakes with ramps)
        this.drawStackedBarChart(id, resultsData.lakes, resultsData.rampsByLake);

        // Render times table
        this.drawTimesTable(id, resultsData.times);
    }

    /**
     * Render all poll result containers on the page
     */
    renderAll() {
        const containers = document.querySelectorAll(this.containerSelector);
        containers.forEach(container => this.renderContainer(container));
    }

    /**
     * Cleanup all chart instances (call when navigating away)
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }
}

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
