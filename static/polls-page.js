/**
 * Polls page JavaScript functionality
 * Initializes poll voting handler, chart renderers, and delete confirmation manager
 */

// Global state
let pollDeleteManager;
let pollResultsRenderer;
let clubPollCharts = {};  // Store Chart.js instances for club polls

/**
 * Render beautiful horizontal bar chart for a club poll
 * Features: gradients, rounded corners, smooth animations, vote labels
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
        chartContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-inbox text-muted" style="font-size: 2.5rem; opacity: 0.5;"></i>
                <p class="text-muted mt-2 mb-0">No votes yet</p>
            </div>`;
        return;
    }

    // Sort by votes descending
    filteredData.sort((a, b) => b.votes - a.votes);

    // Create canvas element
    chartContainer.innerHTML = '<canvas id="clubPollCanvas-' + pollId + '"></canvas>';
    const canvas = document.getElementById('clubPollCanvas-' + pollId);
    const ctx = canvas.getContext('2d');

    // Calculate dynamic height based on number of options
    const barHeight = 50;
    const minHeight = 150;
    const calculatedHeight = Math.max(minHeight, filteredData.length * barHeight + 50);
    canvas.style.height = calculatedHeight + 'px';
    chartContainer.style.height = calculatedHeight + 'px';

    // Assign beautiful colors from shared palette
    const backgroundColors = filteredData.map((_, i) => CHART_COLORS.get(i).base);
    const hoverColors = filteredData.map((_, i) => CHART_COLORS.get(i).light);

    // Create the chart with beautiful styling
    clubPollCharts[pollId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: filteredData.map(d => d.label),
            datasets: [{
                data: filteredData.map(d => d.votes),
                backgroundColor: backgroundColors,
                hoverBackgroundColor: hoverColors,
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false,
                barThickness: 32,
                maxBarThickness: 40
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: { right: 70, left: 5, top: 10, bottom: 10 }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    ...CHART_CONFIG.tooltip,
                    callbacks: {
                        title: function(context) {
                            return '🗳️ ' + context[0].label;
                        },
                        label: function(context) {
                            const votes = context.raw;
                            const percentage = totalVotes > 0 ? ((votes / totalVotes) * 100).toFixed(1) : 0;
                            return votes + ' vote' + (votes !== 1 ? 's' : '') + ' (' + percentage + '%)';
                        },
                        afterBody: function() {
                            return '\n━━━━━━━━━━━━━━━\nTotal: ' + totalVotes + ' votes';
                        }
                    }
                },
                // Use our custom vote labels plugin
                voteLabels: {
                    enabled: true,
                    data: filteredData,
                    totalVotes: totalVotes
                }
            },
            scales: {
                x: {
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
                    ...CHART_CONFIG.scales.y,
                    ticks: {
                        ...CHART_CONFIG.scales.y.ticks,
                        padding: 8,
                        callback: function(value) {
                            const label = this.getLabelForValue(value);
                            return label.length > 25 ? label.substring(0, 22) + '...' : label;
                        }
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
            onHover: function(event, elements) {
                event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
            }
        }
    });
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
