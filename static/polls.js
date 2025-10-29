/**
 * SABC Polls - Public Voting Interface
 * Handles tournament location voting with lake/ramp selection and time voting
 */

// Poll voting functionality
function submitVote(pollId, canVote, userId) {
    if (!canVote) {
        if (!userId) {
            showToast('Please log in to vote.', 'warning');
            setTimeout(() => {
                window.location.href = '/login?next=/polls';
            }, 1500);
        } else {
            showToast('You must be a verified member to vote in polls.', 'warning');
        }
        return;
    }

    const form = document.getElementById(`vote-form-${pollId}`);
    const formData = new FormData(form);

    // Get selected lake and ramp
    const lakeSelect = form.querySelector('select[name="lake"]');
    const rampSelect = form.querySelector('select[name="ramp"]');

    if (!lakeSelect || !lakeSelect.value) {
        showToast('Please select a lake', 'warning');
        return;
    }

    if (!rampSelect || !rampSelect.value) {
        showToast('Please select a ramp', 'warning');
        return;
    }

    // Submit the vote
    fetch(`/polls/${pollId}/vote`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Vote submitted successfully!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.error || 'Error submitting vote', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error submitting vote. Please try again.', 'error');
    });
}

// Lake/ramp selection functionality
function onLakeChange(pollId, lakesAndRamps) {
    const lakeSelect = document.querySelector(`#vote-form-${pollId} select[name="lake"]`);
    const rampSelect = document.querySelector(`#vote-form-${pollId} select[name="ramp"]`);

    if (!lakeSelect || !rampSelect) return;

    const lakeId = lakeSelect.value;

    // Clear ramp options
    rampSelect.innerHTML = '<option value="">-- Select Ramp --</option>';
    rampSelect.disabled = true;

    if (!lakeId || !lakesAndRamps[lakeId]) return;

    // Populate ramps for selected lake
    const ramps = lakesAndRamps[lakeId].ramps || [];
    ramps.forEach(ramp => {
        const option = document.createElement('option');
        option.value = ramp.id;
        option.textContent = ramp.name;
        rampSelect.appendChild(option);
    });

    if (ramps.length > 0) {
        rampSelect.disabled = false;
    }
}

// Chart functionality for tournament polls
function drawLakesChart(resultsData) {
    const container = document.getElementById('lakesChart');
    if (!container) return;

    const data = resultsData.lakes;

    if (!data || data.length === 0) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes yet</div>';
        return;
    }

    // Calculate max votes for percentage
    const maxVotes = Math.max(...data.map(d => d.votes));

    // Build HTML bar chart with clickable bars
    container.innerHTML = data.map(lake => {
        const percentage = (lake.votes / maxVotes) * 100;
        const escapedName = escapeHtml(lake.name);
        // Ensure lake.id is a safe integer to prevent XSS
        const lakeId = parseInt(lake.id, 10);
        if (isNaN(lakeId)) {
            console.error('Invalid lake ID:', lake.id);
            return '';
        }
        return `
            <div class="lake-card mb-2" data-lake-id="${lakeId}" style="cursor: pointer;" onclick="selectLake(${lakeId})">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-semibold">${escapedName}</span>
                    <span class="badge bg-primary">${lake.votes}</span>
                </div>
                <div class="progress" style="height: 25px;">
                    <div class="progress-bar lake-bar bg-success" role="progressbar"
                         style="width: ${percentage}%"
                         aria-valuenow="${lake.votes}"
                         aria-valuemin="0"
                         aria-valuemax="${maxVotes}">
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function drawRampsChart(lakeId) {
    const container = document.getElementById('rampsChart');
    if (!container) return;

    // Get ramps data for selected lake from results
    const resultsData = window.pollResultsData;
    if (!resultsData || !resultsData.ramps) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-arrow-up me-2"></i>Select a lake above to see ramps</div>';
        return;
    }

    const ramps = resultsData.ramps.filter(r => r.lake_id == lakeId);

    if (ramps.length === 0) {
        container.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes for ramps at this lake</div>';
        return;
    }

    // Calculate max votes for percentage
    const maxVotes = Math.max(...ramps.map(r => r.votes));

    // Build HTML bar chart
    container.innerHTML = ramps.map(ramp => {
        const percentage = (ramp.votes / maxVotes) * 100;
        const escapedName = escapeHtml(ramp.name);
        return `
            <div class="mb-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-semibold">${escapedName}</span>
                    <span class="badge bg-primary">${ramp.votes}</span>
                </div>
                <div class="progress" style="height: 25px;">
                    <div class="progress-bar bg-info" role="progressbar"
                         style="width: ${percentage}%"
                         aria-valuenow="${ramp.votes}"
                         aria-valuemin="0"
                         aria-valuemax="${maxVotes}">
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function selectLake(lakeId) {
    // Highlight selected lake
    document.querySelectorAll('.lake-card').forEach(card => {
        card.classList.remove('border', 'border-primary', 'border-2');
        card.style.backgroundColor = '';
    });

    const selectedCard = document.querySelector(`[data-lake-id="${lakeId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('border', 'border-primary', 'border-2');
        selectedCard.style.backgroundColor = 'rgba(13, 110, 253, 0.05)';
    }

    // Update the selected lake label
    const selectedLakeLabel = document.getElementById('selectedLake');
    if (selectedLakeLabel) {
        const lakeName = getLakeName(lakeId);
        selectedLakeLabel.textContent = lakeName;
    }

    // Draw ramps chart for selected lake
    drawRampsChart(lakeId);
}

// No filtering functionality needed - times are independent of lake/ramp choices

// Helper functions
function formatTime12Hour(time24) {
    // Parse time in HH:MM format
    const [hours, minutes] = time24.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${hour12}:${minutes} ${ampm}`;
}

function getLakeName(lakeId) {
    if (!lakeId) return 'Unknown Lake';

    // Try to get from lakesData (array format)
    if (typeof lakesData !== 'undefined' && Array.isArray(lakesData)) {
        const lake = lakesData.find(l => l.id == lakeId);
        if (lake) return lake.name;
    }

    // Try to get from lakesAndRamps (object format) - legacy support
    if (typeof lakesAndRamps !== 'undefined' && lakesAndRamps[lakeId]) {
        return lakesAndRamps[lakeId].name;
    }

    return `Lake ${lakeId}`;
}

function getRampName(rampId) {
    if (!rampId) return 'Unknown Ramp';

    // Try to get from lakesData (array format)
    if (typeof lakesData !== 'undefined' && Array.isArray(lakesData)) {
        for (const lake of lakesData) {
            const ramp = lake.ramps.find(r => r.id == rampId);
            if (ramp) {
                // Apply title case
                return ramp.name.split(' ').map(word =>
                    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
                ).join(' ');
            }
        }
    }

    // Try to get from lakesAndRamps (object format) - legacy support
    if (typeof lakesAndRamps !== 'undefined') {
        for (const lake of Object.values(lakesAndRamps)) {
            const ramp = lake.ramps.find(r => r.id == rampId);
            if (ramp) {
                return ramp.name.split(' ').map(word =>
                    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
                ).join(' ');
            }
        }
    }

    return `Ramp ${rampId}`;
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Process tournament results containers
    const resultsContainers = document.querySelectorAll('.tournament-results-container');

    resultsContainers.forEach(container => {
        const pollId = container.dataset.pollId;
        const pollType = container.dataset.pollType;

        if (pollType !== 'tournament_location') return;

        // Parse option data from hidden elements
        const optionElements = container.querySelectorAll('[data-option-id]');
        const lakes = {};
        const ramps = {};
        const times = {};

        optionElements.forEach(el => {
            const optionData = el.dataset.optionData ? JSON.parse(el.dataset.optionData) : {};
            const voteCount = parseInt(el.dataset.voteCount) || 0;

            if (voteCount === 0) return; // Skip options with no votes

            const lakeId = optionData.lake_id;
            const rampId = optionData.ramp_id;
            const startTime = optionData.start_time;
            const endTime = optionData.end_time;

            // Aggregate lake votes
            if (lakeId) {
                if (!lakes[lakeId]) {
                    lakes[lakeId] = {
                        id: lakeId,
                        name: getLakeName(lakeId),
                        votes: 0
                    };
                }
                lakes[lakeId].votes += voteCount;
            }

            // Aggregate ramp votes
            if (rampId) {
                if (!ramps[rampId]) {
                    ramps[rampId] = {
                        id: rampId,
                        lake_id: lakeId,
                        name: getRampName(rampId),
                        votes: 0
                    };
                }
                ramps[rampId].votes += voteCount;
            }

            // Aggregate time votes
            if (startTime && endTime) {
                const timeKey = `${startTime}-${endTime}`;
                if (!times[timeKey]) {
                    times[timeKey] = {
                        start_time: startTime,
                        weigh_in_time: endTime,
                        votes: 0
                    };
                }
                times[timeKey].votes += voteCount;
            }
        });

        // Convert objects to sorted arrays
        const lakesData = Object.values(lakes).sort((a, b) => b.votes - a.votes);
        const rampsData = Object.values(ramps).sort((a, b) => b.votes - a.votes);
        const timesData = Object.values(times).sort((a, b) => b.votes - a.votes);

        // Create results data object
        const resultsData = {
            lakes: lakesData,
            ramps: rampsData,
            times: timesData
        };

        // Store globally for drilldown functionality
        window.pollResultsData = resultsData;

        // Draw charts if we have data
        if (lakesData.length > 0 || rampsData.length > 0 || timesData.length > 0) {
            // Find canvas elements within this container
            const lakesCanvas = container.querySelector('#lakesChart');
            const rampsCanvas = container.querySelector('#rampsChart');
            const timesCanvas = container.querySelector('#timeTable');

            // Draw lakes chart
            if (lakesCanvas && lakesData.length > 0) {
                drawLakesChart(resultsData);
            }

            // Draw times table
            if (timesCanvas && timesData.length > 0) {
                const tbody = timesCanvas.querySelector('tbody');
                if (tbody) {
                    tbody.innerHTML = '';
                    timesData.forEach(time => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="small">${formatTime12Hour(time.start_time)}</td>
                            <td class="small">${formatTime12Hour(time.weigh_in_time)}</td>
                            <td class="small text-center">
                                <span class="badge bg-primary">${time.votes}</span>
                            </td>
                        `;
                        tbody.appendChild(row);
                    });
                }
            }

            // Auto-expand ramps if only one lake has votes
            if (lakesData.length === 1 && rampsData.length > 0) {
                selectLake(lakesData[0].id);
            }

            // Show the results container
            container.classList.remove('d-none');
        }
    });
});
