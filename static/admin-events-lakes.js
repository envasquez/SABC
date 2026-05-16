/**
 * Admin Events - Lake/Ramp Loading Module
 * Handles loading lakes data and populating lake/ramp dropdowns
 */

(function() {
    'use strict';

    // Shared lakes data cache
    let lakesData = [];

    /**
     * Populate a lake <select> element with options from lakes data
     * @param {HTMLSelectElement|null} selectEl - The select element to populate
     * @param {Array} lakes - Array of lake objects ({name, key})
     * @param {string} emptyLabel - Label for the leading empty option
     */
    function populateLakeSelect(selectEl, lakes, emptyLabel) {
        if (!selectEl) return;
        selectEl.innerHTML = '<option value="">' + emptyLabel + '</option>';
        lakes.forEach(lake => {
            const option = document.createElement('option');
            option.value = lake.name;
            option.textContent = lake.name;
            option.dataset.lakeKey = lake.key;
            selectEl.appendChild(option);
        });
    }

    /**
     * Load lakes data from API and populate all lake dropdowns
     */
    function loadLakes() {
        fetch('/api/lakes', { credentials: 'same-origin' })
            .then(response => {
                if (!response.ok) throw new Error('Failed to load lakes');
                return response.json();
            })
            .then(lakes => {
                lakesData = lakes;
                // Populate create form lake select
                populateLakeSelect(
                    document.getElementById('lake_name'),
                    lakes,
                    '-- Select Lake --'
                );

                // Populate edit form lake select
                populateLakeSelect(
                    document.getElementById('edit_lake_name'),
                    lakes,
                    '-- Select Lake --'
                );

                // Populate other tournament lake select
                loadLakesForOtherTournament();
            })
            .catch(error => {
                console.error('Error loading lakes:', error);
                if (typeof showToast === 'function') {
                    showToast('Error loading lakes. Please refresh the page.', 'error');
                }
            });
    }

    /**
     * Load boat ramps for a selected lake using LakeRampSelector component
     * Fetches ramps from API and populates the specified select element
     *
     * @param {string} lakeName - Name of the lake to load ramps for
     * @param {string} rampSelectId - ID of the select element to populate (default: 'edit_ramp_name')
     * @returns {Promise<void>} Promise that resolves when ramps are loaded
     */
    async function loadRamps(lakeName, rampSelectId = 'edit_ramp_name') {
        // Create a temporary lake select ID (not used but required by component)
        const tempLakeId = `temp_lake_for_${rampSelectId}`;

        const selector = new LakeRampSelector({
            lakeSelectId: tempLakeId,
            rampSelectId: rampSelectId,
            lakesData: lakesData,
            useApi: true
        });

        await selector.loadRampsForLake(lakeName);
    }

    /**
     * Populate other tournament lake dropdown from cached lakesData
     */
    function loadLakesForOtherTournament() {
        const lakeSelect = document.getElementById('other_lake_name');
        if (lakeSelect && lakesData.length > 0) {
            populateLakeSelect(lakeSelect, lakesData, '-- Select Lake (Optional) --');
        }
    }

    /**
     * Get the current lakes data cache
     * @returns {Array} The cached lakes data
     */
    function getLakesData() {
        return lakesData;
    }

    /**
     * Set the lakes data cache (used when loading data externally)
     * @param {Array} data - Lakes data to cache
     */
    function setLakesData(data) {
        lakesData = data;
    }

    // Export functions consumed by admin-events.js (cross-file dependency)
    window.loadLakes = loadLakes;
    window.loadRamps = loadRamps;
    window.loadLakesForOtherTournament = loadLakesForOtherTournament;
    window.getLakesData = getLakesData;
    window.setLakesData = setLakesData;
})();
