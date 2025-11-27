/**
 * Home Page Poll Results Visualization
 *
 * This module handles the visualization of poll results for upcoming tournaments
 * on the home page, including lakes, ramps, and tournament times voting results.
 */

// Global state for lakes data
let lakesDataGlobal = [];

/**
 * Initialize home page poll visualization
 * @param {Object} config - Configuration object
 * @param {Array} config.lakesData - Array of lakes with ramps data
 */
function initializeHomePolls(config) {
    lakesDataGlobal = config.lakesData || [];

    // Render poll results for all tournament containers
    renderAllPollResults();

    // Handle tab switching for pagination
    handleTabSwitching();
}

// Note: formatTime12Hour, getLakeName, and getRampName are defined in utils.js
// Local wrapper functions that use the global lakesDataGlobal variable

/**
 * Get lake name by ID using global lakes data
 * @param {number} lakeId - Lake ID
 * @returns {string} Lake name or fallback
 */
function getLakeNameHome(lakeId) {
    return getLakeName(lakesDataGlobal, lakeId);
}

/**
 * Get ramp name by ID using global lakes data
 * @param {number} rampId - Ramp ID
 * @returns {string} Ramp name or fallback
 */
function getRampNameHome(rampId) {
    return getRampName(lakesDataGlobal, rampId);
}

/**
 * Draw lakes voting chart for a tournament
 * @param {HTMLElement} container - Container element
 * @param {Object} resultsData - Poll results data
 * @param {number} tournamentId - Tournament ID
 */
function drawLakesChartHome(container, resultsData, tournamentId) {
    const chartContainer = container.querySelector(`#lakesChart-${tournamentId}`);
    if (!chartContainer) return;

    const data = resultsData.lakes;
    if (!data || data.length === 0) {
        chartContainer.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes yet</div>';
        return;
    }

    const maxVotes = Math.max(...data.map(d => d.votes));
    chartContainer.innerHTML = data.map(lake => {
        const percentage = (lake.votes / maxVotes) * 100;
        return `
            <div class="lake-card mb-2" data-lake-id="${lake.id}" style="cursor: pointer;" onclick="selectLakeHome(${lake.id}, ${tournamentId})">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-semibold">${escapeHtml(lake.name)}</span>
                    <span class="badge bg-primary">${lake.votes}</span>
                </div>
                <div class="progress" style="height: 25px;">
                    <div class="progress-bar lake-bar bg-success" role="progressbar" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Draw ramps voting chart for a selected lake
 * @param {number} lakeId - Lake ID
 * @param {number} tournamentId - Tournament ID
 */
function drawRampsChartHome(lakeId, tournamentId) {
    const container = document.querySelector(`#rampsChart-${tournamentId}`);
    if (!container) return;

    const resultsData = window[`pollResultsData_${tournamentId}`];
    if (!resultsData || !resultsData.ramps) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-arrow-up me-2"></i>Select a lake above to see ramps</div>';
        return;
    }

    const ramps = resultsData.ramps.filter(r => r.lake_id == lakeId);
    if (ramps.length === 0) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes for ramps at this lake</div>';
        return;
    }

    const maxVotes = Math.max(...ramps.map(r => r.votes));
    container.innerHTML = ramps.map(ramp => {
        const percentage = (ramp.votes / maxVotes) * 100;
        return `
            <div class="mb-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-semibold">${escapeHtml(ramp.name)}</span>
                    <span class="badge bg-primary">${ramp.votes}</span>
                </div>
                <div class="progress" style="height: 25px;">
                    <div class="progress-bar bg-info" role="progressbar" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Handle lake selection for a tournament
 * @param {number} lakeId - Lake ID
 * @param {number} tournamentId - Tournament ID
 */
function selectLakeHome(lakeId, tournamentId) {
    const container = document.querySelector(`[data-tournament-id="${tournamentId}"]`);
    if (!container) return;

    // Remove selection from all lake cards
    container.querySelectorAll('.lake-card').forEach(card => {
        card.classList.remove('border', 'border-primary', 'border-2');
        card.style.backgroundColor = '';
    });

    // Add selection to clicked lake card
    const selectedCard = container.querySelector(`[data-lake-id="${lakeId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('border', 'border-primary', 'border-2');
        selectedCard.style.backgroundColor = 'rgba(13, 110, 253, 0.05)';
    }

    // Update selected lake label
    const selectedLakeLabel = container.querySelector(`#selectedLake-${tournamentId}`);
    if (selectedLakeLabel) {
        selectedLakeLabel.textContent = getLakeNameHome(lakeId);
    }

    // Draw ramps chart for selected lake
    drawRampsChartHome(lakeId, tournamentId);
}

/**
 * Render poll results for all tournament containers
 */
function renderAllPollResults() {
    const resultsContainers = document.querySelectorAll('.tournament-results-container-home');

    resultsContainers.forEach(container => {
        const tournamentId = container.dataset.tournamentId;
        const optionElements = container.querySelectorAll('.poll-option-data');

        const lakes = {};
        const ramps = {};
        const times = {};

        // Aggregate votes from poll options
        optionElements.forEach(el => {
            const pollOptionData = el.dataset.optionData ? JSON.parse(el.dataset.optionData) : {};
            const voteCount = parseInt(el.dataset.voteCount) || 0;

            if (voteCount === 0) return;

            const lakeId = pollOptionData.lake_id;
            const rampId = pollOptionData.ramp_id;
            const startTime = pollOptionData.start_time;
            const endTime = pollOptionData.end_time;

            // Aggregate lake votes
            if (lakeId) {
                if (!lakes[lakeId]) {
                    lakes[lakeId] = { id: lakeId, name: getLakeNameHome(lakeId), votes: 0 };
                }
                lakes[lakeId].votes += voteCount;
            }

            // Aggregate ramp votes
            if (rampId) {
                if (!ramps[rampId]) {
                    ramps[rampId] = { id: rampId, lake_id: lakeId, name: getRampNameHome(rampId), votes: 0 };
                }
                ramps[rampId].votes += voteCount;
            }

            // Aggregate time votes
            if (startTime && endTime) {
                const timeKey = `${startTime}-${endTime}`;
                if (!times[timeKey]) {
                    times[timeKey] = { start_time: startTime, weigh_in_time: endTime, votes: 0 };
                }
                times[timeKey].votes += voteCount;
            }
        });

        // Sort by votes (descending)
        const lakesArray = Object.values(lakes).sort((a, b) => b.votes - a.votes);
        const rampsArray = Object.values(ramps).sort((a, b) => b.votes - a.votes);
        const timesArray = Object.values(times).sort((a, b) => b.votes - a.votes);

        // Store results data globally for this tournament
        const resultsData = { lakes: lakesArray, ramps: rampsArray, times: timesArray };
        window[`pollResultsData_${tournamentId}`] = resultsData;

        // Render visualizations if there are votes
        if (lakesArray.length > 0 || rampsArray.length > 0 || timesArray.length > 0) {
            drawLakesChartHome(container, resultsData, tournamentId);

            // Render times table
            const timesTable = container.querySelector(`#timeTable-${tournamentId} tbody`);
            if (timesTable && timesArray.length > 0) {
                timesTable.innerHTML = timesArray.map(time => `
                    <tr>
                        <td class="small">${formatTime12Hour(time.start_time)}</td>
                        <td class="small">${formatTime12Hour(time.weigh_in_time)}</td>
                        <td class="small text-center"><span class="badge bg-primary">${time.votes}</span></td>
                    </tr>
                `).join('');
            }

            // Auto-select lake if there's only one option
            if (lakesArray.length === 1 && rampsArray.length > 0) {
                selectLakeHome(lakesArray[0].id, tournamentId);
            }
        }
    });
}

/**
 * Handle tab switching based on URL pagination parameter
 */
function handleTabSwitching() {
    const urlParams = new URLSearchParams(window.location.search);
    const pageParam = urlParams.get('p');

    // If there's a page parameter (pagination), switch to Completed tab
    if (pageParam) {
        const completedTab = document.getElementById('completed-tab');
        const upcomingTab = document.getElementById('upcoming-tab');
        const completedPane = document.getElementById('completed-pane');
        const upcomingPane = document.getElementById('upcoming-pane');

        if (completedTab && upcomingTab && completedPane && upcomingPane) {
            // Activate Completed tab
            completedTab.classList.add('active');
            completedTab.setAttribute('aria-selected', 'true');
            upcomingTab.classList.remove('active');
            upcomingTab.setAttribute('aria-selected', 'false');

            // Show Completed pane, hide Upcoming pane
            completedPane.classList.add('show', 'active');
            upcomingPane.classList.remove('show', 'active');
        }
    }
}

// Export functions to global scope for onclick handlers
window.initializeHomePolls = initializeHomePolls;
window.selectLakeHome = selectLakeHome;
