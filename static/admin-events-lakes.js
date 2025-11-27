/**
 * Admin Events - Lake/Ramp Loading Module
 * Handles loading lakes data and populating lake/ramp dropdowns
 */

// Shared lakes data cache
let lakesData = [];

/**
 * Load lakes data from API and populate all lake dropdowns
 */
function loadLakes() {
    fetch('/api/lakes')
        .then(response => response.json())
        .then(lakes => {
            lakesData = lakes;
            // Populate create form lake select
            const createLakeSelect = document.getElementById('lake_name');
            if (createLakeSelect) {
                createLakeSelect.innerHTML = '<option value="">-- Select Lake --</option>';
                lakes.forEach(lake => {
                    const option = document.createElement('option');
                    option.value = lake.name;
                    option.textContent = lake.name;
                    option.dataset.lakeKey = lake.key;
                    createLakeSelect.appendChild(option);
                });
            }

            // Populate edit form lake select
            const editLakeSelect = document.getElementById('edit_lake_name');
            if (editLakeSelect) {
                editLakeSelect.innerHTML = '<option value="">-- Select Lake --</option>';
                lakes.forEach(lake => {
                    const option = document.createElement('option');
                    option.value = lake.name;
                    option.textContent = lake.name;
                    option.dataset.lakeKey = lake.key;
                    editLakeSelect.appendChild(option);
                });
            }

            // Populate other tournament lake select
            loadLakesForOtherTournament();
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
        lakeSelect.innerHTML = '<option value="">-- Select Lake (Optional) --</option>';
        lakesData.forEach(lake => {
            const option = document.createElement('option');
            option.value = lake.name;
            option.textContent = lake.name;
            option.dataset.lakeKey = lake.key;
            lakeSelect.appendChild(option);
        });
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
