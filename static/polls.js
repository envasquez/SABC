/**
 * SABC Polls - Public Voting Interface
 * Handles tournament location voting with lake/ramp selection and time voting
 */

// Poll voting functionality
function submitVote(pollId, canVote, userId) {
    if (!canVote) {
        if (!userId) {
            alert('Please log in to vote.');
            window.location.href = '/login?next=/polls';
        } else {
            alert('You must be a verified member to vote in polls.');
        }
        return;
    }

    const form = document.getElementById(`vote-form-${pollId}`);
    const formData = new FormData(form);

    // Get selected lake and ramp
    const lakeSelect = form.querySelector('select[name="lake"]');
    const rampSelect = form.querySelector('select[name="ramp"]');

    if (!lakeSelect || !lakeSelect.value) {
        alert('Please select a lake');
        return;
    }

    if (!rampSelect || !rampSelect.value) {
        alert('Please select a ramp');
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
            location.reload();
        } else {
            alert(data.error || 'Error submitting vote');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error submitting vote. Please try again.');
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
    const canvas = document.getElementById('lakesChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const data = resultsData.lakes;

    if (!data || data.length === 0) {
        ctx.font = '16px Arial';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText('No votes yet', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Simple bar chart
    const maxVotes = Math.max(...data.map(d => d.votes));
    const barHeight = 30;
    const barSpacing = 10;
    const chartHeight = data.length * (barHeight + barSpacing);

    canvas.height = chartHeight;

    data.forEach((lake, index) => {
        const y = index * (barHeight + barSpacing);
        const barWidth = (lake.votes / maxVotes) * (canvas.width - 200);

        // Draw bar
        ctx.fillStyle = '#375a7f';
        ctx.fillRect(100, y, barWidth, barHeight);

        // Draw label
        ctx.fillStyle = '#fff';
        ctx.font = '14px Arial';
        ctx.textAlign = 'right';
        ctx.fillText(lake.name, 95, y + barHeight / 2 + 5);

        // Draw vote count
        ctx.textAlign = 'left';
        ctx.fillText(lake.votes, barWidth + 105, y + barHeight / 2 + 5);
    });
}

function drawRampsChart(lakeId) {
    const canvas = document.getElementById('rampsChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Get ramps data for selected lake from results
    const resultsData = window.pollResultsData;
    if (!resultsData || !resultsData.ramps) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText('Select a lake to see ramps', canvas.width / 2, canvas.height / 2);
        return;
    }

    const ramps = resultsData.ramps.filter(r => r.lake_id == lakeId);

    if (ramps.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText('No votes for ramps at this lake', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Draw bar chart for ramps
    const maxVotes = Math.max(...ramps.map(r => r.votes));
    const barHeight = 30;
    const barSpacing = 10;
    const chartHeight = ramps.length * (barHeight + barSpacing);

    canvas.height = chartHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ramps.forEach((ramp, index) => {
        const y = index * (barHeight + barSpacing);
        const barWidth = (ramp.votes / maxVotes) * (canvas.width - 200);

        // Draw bar
        ctx.fillStyle = '#00bc8c';
        ctx.fillRect(100, y, barWidth, barHeight);

        // Draw label
        ctx.fillStyle = '#fff';
        ctx.font = '14px Arial';
        ctx.textAlign = 'right';
        ctx.fillText(ramp.name, 95, y + barHeight / 2 + 5);

        // Draw vote count
        ctx.textAlign = 'left';
        ctx.fillText(ramp.votes, barWidth + 105, y + barHeight / 2 + 5);
    });
}

function drawTimesChart(resultsData) {
    const canvas = document.getElementById('timesChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const data = resultsData.times;

    if (!data || data.length === 0) {
        ctx.font = '16px Arial';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText('No time votes yet', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Simple bar chart for times
    const maxVotes = Math.max(...data.map(d => d.votes));
    const barHeight = 30;
    const barSpacing = 10;
    const chartHeight = data.length * (barHeight + barSpacing);

    canvas.height = chartHeight;

    data.forEach((time, index) => {
        const y = index * (barHeight + barSpacing);
        const barWidth = (time.votes / maxVotes) * (canvas.width - 200);

        // Draw bar
        ctx.fillStyle = '#f39c12';
        ctx.fillRect(100, y, barWidth, barHeight);

        // Draw label
        ctx.fillStyle = '#fff';
        ctx.font = '14px Arial';
        ctx.textAlign = 'right';
        const timeLabel = `${time.start_time} - ${time.weigh_in_time}`;
        ctx.fillText(timeLabel, 95, y + barHeight / 2 + 5);

        // Draw vote count
        ctx.textAlign = 'left';
        ctx.fillText(time.votes, barWidth + 105, y + barHeight / 2 + 5);
    });
}

function selectLake(lakeId, lakeData) {
    // Highlight selected lake
    document.querySelectorAll('.lake-card').forEach(card => {
        card.style.boxShadow = '';
    });
    document.querySelector(`[data-lake-id="${lakeId}"] .lake-bar`).style.boxShadow = '0 0 0 3px rgba(255,255,255,0.3)';

    // Draw ramps chart for selected lake
    drawRampsChart(lakeId);
}

// No filtering functionality needed - times are independent of lake/ramp choices

// Lake drill-down functionality
function drillDownLake(lakeId, lakeData) {
    // Redirect to the new selectLake functionality
    selectLake(lakeId, lakeData);
}

// Admin vote management moved to edit poll view

// Helper functions
function getLakeName(lakeId) {
    if (!lakeId) return 'Unknown Lake';

    // Try to get from lakesAndRamps if available
    if (typeof lakesAndRamps !== 'undefined' && lakesAndRamps[lakeId]) {
        return lakesAndRamps[lakeId].name;
    }

    // Fallback: extract from option text
    const lakeNames = {
        '1': 'Lake Travis',
        '3': 'Bastrop Lake',
        '4': 'Walter E. Long Lake',
        '16': 'Belton Lake'
    };

    return lakeNames[lakeId] || `Lake ${lakeId}`;
}

function getRampName(rampId) {
    if (!rampId) return 'Unknown Ramp';

    // Try to get from lakesAndRamps if available
    if (typeof lakesAndRamps !== 'undefined') {
        for (const lake of Object.values(lakesAndRamps)) {
            const ramp = lake.ramps.find(r => r.id == rampId);
            if (ramp) {
                // Apply title case to match backend formatting
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
    // Draw initial charts if results data is available
    if (typeof pollResultsData !== 'undefined') {
        drawLakesChart(pollResultsData);
        drawTimesChart(pollResultsData);
    }
});
