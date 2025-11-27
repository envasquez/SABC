/**
 * Polls page JavaScript functionality
 * Initializes poll voting handler and delete confirmation manager
 */

// Initialize delete confirmation manager
let pollDeleteManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('[SABC] Polls page: DOMContentLoaded fired');

    // Get lakes data from data attribute
    const lakesDataElement = document.getElementById('lakes-data');
    const lakesData = lakesDataElement ? JSON.parse(lakesDataElement.dataset.lakes || '[]') : [];

    if (!lakesData || lakesData.length === 0) {
        console.warn('[SABC] Lakes data not loaded or empty');
    } else {
        console.log('[SABC] Lakes data loaded:', lakesData.length, 'lakes');
    }

    // Initialize poll voting handler
    const pollVotingHandler = new PollVotingHandler(lakesData);

    // Populate all lake dropdowns with options
    const allLakeSelects = document.querySelectorAll('select[data-poll-lake]');
    console.log('[SABC] Found', allLakeSelects.length, 'lake select dropdowns');

    allLakeSelects.forEach(lakeSelect => {
        lakesData.forEach(lake => {
            const option = document.createElement('option');
            option.value = lake.id;
            option.textContent = lake.name;
            lakeSelect.appendChild(option);
        });
    });

    // Initialize the poll voting handler (sets up all event listeners)
    pollVotingHandler.initialize();

    console.log('[SABC] Poll voting handler initialized successfully');

    // Render tournament poll results
    renderPollResults(lakesData);

    // Initialize delete confirmation manager
    pollDeleteManager = new DeleteConfirmationManager({
        modalId: 'deletePollModal',
        itemNameElementId: 'deletePollTitle',
        confirmInputId: 'deletePollConfirmInput',
        confirmButtonId: 'confirmDeletePollBtn',
        deleteUrlTemplate: (id) => `/admin/polls/${id}`,
        onSuccess: () => location.reload(),
        onError: (error) => showToast(`Error deleting poll: ${error}`, 'error')
    });
});

function deletePoll(pollId, pollTitle) {
    pollDeleteManager.confirm(pollId, pollTitle);
}

/**
 * Render tournament poll results visualization
 * @param {Array} lakesData - Array of lakes with ramps
 */
function renderPollResults(lakesData) {
    var containers = document.querySelectorAll('.tournament-results-container');

    containers.forEach(function(container) {
        var pollId = container.dataset.pollId;
        var optionElements = container.querySelectorAll('.poll-option-data');

        var lakes = {};
        var ramps = {};
        var times = {};

        // Aggregate votes from poll options
        optionElements.forEach(function(el) {
            var optionData = {};
            try {
                optionData = el.dataset.optionData ? JSON.parse(el.dataset.optionData) : {};
            } catch (e) {
                console.error('[SABC] Error parsing option data:', e);
            }
            var voteCount = parseInt(el.dataset.voteCount) || 0;

            if (voteCount === 0) return;

            var lakeId = optionData.lake_id;
            var rampId = optionData.ramp_id;
            var startTime = optionData.start_time;
            var endTime = optionData.end_time;

            // Aggregate lake votes
            if (lakeId) {
                if (!lakes[lakeId]) {
                    lakes[lakeId] = { id: lakeId, name: getLakeName(lakesData, lakeId), votes: 0 };
                }
                lakes[lakeId].votes += voteCount;
            }

            // Aggregate ramp votes
            if (rampId) {
                if (!ramps[rampId]) {
                    ramps[rampId] = { id: rampId, lake_id: lakeId, name: getRampName(lakesData, rampId), votes: 0 };
                }
                ramps[rampId].votes += voteCount;
            }

            // Aggregate time votes
            if (startTime && endTime) {
                var timeKey = startTime + '-' + endTime;
                if (!times[timeKey]) {
                    times[timeKey] = { start_time: startTime, end_time: endTime, votes: 0 };
                }
                times[timeKey].votes += voteCount;
            }
        });

        // Sort by votes (descending)
        var lakesArray = Object.values(lakes).sort(function(a, b) { return b.votes - a.votes; });
        var rampsArray = Object.values(ramps).sort(function(a, b) { return b.votes - a.votes; });
        var timesArray = Object.values(times).sort(function(a, b) { return b.votes - a.votes; });

        // Store results data globally for this poll
        window['pollResultsData_' + pollId] = { lakes: lakesArray, ramps: rampsArray, times: timesArray };

        // Render lakes chart
        drawLakesChart(pollId, lakesArray);

        // Render times table
        drawTimesTable(pollId, timesArray);

        // Auto-select lake with most votes
        if (lakesArray.length > 0 && rampsArray.length > 0) {
            selectLakePoll(pollId, lakesArray[0].id);
        }
    });
}

// Note: getLakeName, getRampName, and formatTime12Hour are defined in utils.js

function drawLakesChart(pollId, lakesArray) {
    var chartContainer = document.getElementById('lakesChart-' + pollId);
    if (!chartContainer) return;

    if (!lakesArray || lakesArray.length === 0) {
        chartContainer.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes yet</div>';
        return;
    }

    var maxVotes = Math.max.apply(null, lakesArray.map(function(d) { return d.votes; }));
    chartContainer.innerHTML = lakesArray.map(function(lake) {
        var percentage = (lake.votes / maxVotes) * 100;
        return '<div class="lake-card mb-2" data-lake-id="' + lake.id + '" style="cursor: pointer;" onclick="selectLakePoll(' + pollId + ', ' + lake.id + ')">' +
            '<div class="d-flex justify-content-between align-items-center mb-1">' +
                '<span class="fw-semibold">' + escapeHtml(lake.name) + '</span>' +
                '<span class="badge bg-primary">' + lake.votes + '</span>' +
            '</div>' +
            '<div class="progress" style="height: 25px;">' +
                '<div class="progress-bar lake-bar bg-success" role="progressbar" style="width: ' + percentage + '%"></div>' +
            '</div>' +
        '</div>';
    }).join('');
}

function drawRampsChart(pollId, lakeId) {
    var container = document.getElementById('rampsChart-' + pollId);
    if (!container) return;

    var resultsData = window['pollResultsData_' + pollId];
    if (!resultsData || !resultsData.ramps) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-arrow-up me-2"></i>Select a lake above to see ramps</div>';
        return;
    }

    var ramps = resultsData.ramps.filter(function(r) { return r.lake_id == lakeId; });
    if (ramps.length === 0) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes for ramps at this lake</div>';
        return;
    }

    var maxVotes = Math.max.apply(null, ramps.map(function(r) { return r.votes; }));
    container.innerHTML = ramps.map(function(ramp) {
        var percentage = (ramp.votes / maxVotes) * 100;
        return '<div class="mb-2">' +
            '<div class="d-flex justify-content-between align-items-center mb-1">' +
                '<span class="fw-semibold">' + escapeHtml(ramp.name) + '</span>' +
                '<span class="badge bg-primary">' + ramp.votes + '</span>' +
            '</div>' +
            '<div class="progress" style="height: 25px;">' +
                '<div class="progress-bar bg-info" role="progressbar" style="width: ' + percentage + '%"></div>' +
            '</div>' +
        '</div>';
    }).join('');
}

function drawTimesTable(pollId, timesArray) {
    var tableBody = document.querySelector('#timeTable-' + pollId + ' tbody');
    if (!tableBody) return;

    if (!timesArray || timesArray.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="3" class="text-secondary text-center py-3"><i class="bi bi-inbox me-2"></i>No votes</td></tr>';
        return;
    }

    tableBody.innerHTML = timesArray.map(function(time) {
        return '<tr>' +
            '<td class="small">' + formatTime12Hour(time.start_time) + '</td>' +
            '<td class="small">' + formatTime12Hour(time.end_time) + '</td>' +
            '<td class="small text-center"><span class="badge bg-primary">' + time.votes + '</span></td>' +
        '</tr>';
    }).join('');
}

function selectLakePoll(pollId, lakeId) {
    var container = document.querySelector('[data-poll-id="' + pollId + '"].tournament-results-container');
    if (!container) return;

    // Remove selection from all lake cards
    container.querySelectorAll('.lake-card').forEach(function(card) {
        card.classList.remove('border', 'border-primary', 'border-2');
        card.style.backgroundColor = '';
    });

    // Add selection to clicked lake card
    var selectedCard = container.querySelector('[data-lake-id="' + lakeId + '"]');
    if (selectedCard) {
        selectedCard.classList.add('border', 'border-primary', 'border-2');
        selectedCard.style.backgroundColor = 'rgba(13, 110, 253, 0.05)';
    }

    // Update selected lake label
    var selectedLakeLabel = document.getElementById('selectedLake-' + pollId);
    if (selectedLakeLabel) {
        var resultsData = window['pollResultsData_' + pollId];
        if (resultsData && resultsData.lakes) {
            var lake = resultsData.lakes.find(function(l) { return l.id == lakeId; });
            if (lake) selectedLakeLabel.textContent = lake.name;
        }
    }

    // Draw ramps chart for selected lake
    drawRampsChart(pollId, lakeId);
}

// Expose selectLakePoll to global scope for onclick handlers
window.selectLakePoll = selectLakePoll;
