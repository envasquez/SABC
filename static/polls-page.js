/**
 * Polls page JavaScript functionality
 * Initializes poll voting handler, chart renderers, and delete confirmation manager
 */

// Global state
let pollDeleteManager;
let pollResultsRenderer;
let clubPollCharts = {};  // Store Chart.js instances for club polls

// Color palette for club poll bars (matches tournament chart colors)
const CLUB_POLL_COLORS = [
    '#2E86AB',  // Steel blue
    '#A23B72',  // Raspberry
    '#F18F01',  // Orange
    '#C73E1D',  // Red
    '#3B1F2B',  // Dark purple
    '#95C623',  // Lime green
    '#5C4D7D',  // Purple
    '#E94F37',  // Coral
    '#1B998B',  // Teal
    '#FF6B6B'   // Salmon
];

/**
 * Render horizontal bar chart for a club poll
 * @param {HTMLElement} dataElement - Element containing poll data attributes
 */
function renderClubPollChart(dataElement) {
    const pollId = dataElement.dataset.pollId;
    const options = JSON.parse(dataElement.dataset.options || '[]');
    const votes = JSON.parse(dataElement.dataset.votes || '[]');
    const totalVotes = parseInt(dataElement.dataset.totalVotes) || 0;

    const chartContainer = document.getElementById('clubPollChart-' + pollId);
    if (!chartContainer) return;

    // Destroy existing chart if any
    if (clubPollCharts[pollId]) {
        clubPollCharts[pollId].destroy();
    }

    // Filter out options with zero votes for cleaner display
    const filteredData = options.map((opt, i) => ({
        label: opt,
        votes: votes[i] || 0
    })).filter(d => d.votes > 0);

    if (filteredData.length === 0) {
        chartContainer.innerHTML = '<div class="text-secondary text-center py-4"><i class="bi bi-inbox me-2"></i>No votes yet</div>';
        return;
    }

    // Sort by votes descending
    filteredData.sort((a, b) => b.votes - a.votes);

    // Create canvas element
    chartContainer.innerHTML = '<canvas id="clubPollCanvas-' + pollId + '"></canvas>';
    const canvas = document.getElementById('clubPollCanvas-' + pollId);
    const ctx = canvas.getContext('2d');

    // Calculate dynamic height based on number of options
    const barHeight = 45;
    const minHeight = 120;
    const calculatedHeight = Math.max(minHeight, filteredData.length * barHeight + 60);
    canvas.style.height = calculatedHeight + 'px';
    chartContainer.style.height = calculatedHeight + 'px';

    // Assign colors to each option
    const backgroundColors = filteredData.map((_, i) => CLUB_POLL_COLORS[i % CLUB_POLL_COLORS.length]);

    // Create the chart
    clubPollCharts[pollId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: filteredData.map(d => d.label),
            datasets: [{
                data: filteredData.map(d => d.votes),
                backgroundColor: backgroundColors,
                borderColor: backgroundColors,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',  // Horizontal bars
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false  // No legend needed for single dataset
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const votes = context.raw;
                            const percentage = totalVotes > 0 ? ((votes / totalVotes) * 100).toFixed(1) : 0;
                            return votes + ' vote' + (votes !== 1 ? 's' : '') + ' (' + percentage + '%)';
                        }
                    }
                },
                // Custom plugin to draw vote count at end of bars
                datalabels: false  // Disable if plugin exists
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            size: 11
                        }
                    },
                    title: {
                        display: true,
                        text: 'Votes',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0,0,0,0.05)'
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 12
                        },
                        // Truncate long labels
                        callback: function(value, index) {
                            const label = this.getLabelForValue(value);
                            return label.length > 30 ? label.substring(0, 27) + '...' : label;
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            },
            // Mobile-friendly touch interactions
            interaction: {
                mode: 'nearest',
                axis: 'y',
                intersect: false
            },
            animation: {
                duration: 500,
                easing: 'easeOutQuart',
                // Draw vote counts after animation completes
                onComplete: function() {
                    drawVoteCounts(this, filteredData, totalVotes);
                }
            }
        }
    });
}

/**
 * Draw vote counts at the end of each bar
 * @param {Chart} chart - Chart.js instance
 * @param {Array} data - Filtered poll data
 * @param {number} totalVotes - Total votes in poll
 */
function drawVoteCounts(chart, data, totalVotes) {
    const ctx = chart.ctx;
    const meta = chart.getDatasetMeta(0);

    ctx.save();
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    meta.data.forEach((bar, index) => {
        const votes = data[index].votes;
        const percentage = totalVotes > 0 ? ((votes / totalVotes) * 100).toFixed(0) : 0;
        const text = votes + ' (' + percentage + '%)';

        // Position text at end of bar with small padding
        const x = bar.x + 5;
        const y = bar.y;

        // Draw text with shadow for readability
        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        ctx.fillText(text, x, y);
    });

    ctx.restore();
}

/**
 * Initialize all club poll charts on the page
 */
function initializeClubPollCharts() {
    const dataElements = document.querySelectorAll('.club-poll-data');
    dataElements.forEach(el => renderClubPollChart(el));
}

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

    // Initialize tournament poll results renderer using shared PollResultsRenderer class
    pollResultsRenderer = new PollResultsRenderer({
        lakesData: lakesData,
        containerSelector: '.tournament-results-container',
        idAttribute: 'pollId'
    });
    pollResultsRenderer.renderAll();

    // Initialize club poll horizontal bar charts
    initializeClubPollCharts();

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
