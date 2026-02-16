/**
 * Polls page JavaScript functionality
 * Initializes poll voting handler, chart renderers, and delete confirmation manager
 */

/**
 * Global state for poll page
 * @type {DeleteConfirmationManager|undefined}
 */
let pollDeleteManager;

/**
 * Poll results renderer instance
 * @type {PollResultsRenderer|undefined}
 */
let pollResultsRenderer;

/**
 * Store Chart.js instances for club polls, keyed by poll ID
 * @type {Object.<string, Chart>}
 */
let clubPollCharts = {};

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
    // Use larger bar height on mobile to accommodate more wrapped lines
    const isMobile = window.innerWidth < 576;
    const barHeight = isMobile ? 75 : 65;
    const minHeight = 150;
    const calculatedHeight = Math.max(minHeight, filteredData.length * barHeight + 50);
    canvas.style.height = calculatedHeight + 'px';
    chartContainer.style.height = calculatedHeight + 'px';

    // Assign beautiful colors from shared palette
    const backgroundColors = filteredData.map((_, i) => CHART_COLORS.get(i).base);
    const hoverColors = filteredData.map((_, i) => CHART_COLORS.get(i).light);

    // Helper function to wrap long labels into multiple lines
    function wrapLabel(label, maxChars) {
        if (!label || label.length <= maxChars) return label;
        const words = label.split(' ');
        const lines = [];
        let currentLine = '';
        for (const word of words) {
            if ((currentLine + ' ' + word).trim().length <= maxChars) {
                currentLine = (currentLine + ' ' + word).trim();
            } else {
                if (currentLine) lines.push(currentLine);
                currentLine = word;
            }
        }
        if (currentLine) lines.push(currentLine);
        return lines;
    }

    // Determine responsive wrap limit based on screen width
    // On narrow mobile screens, wrap at shorter lengths to prevent cutoff
    const screenWidth = window.innerWidth;
    let wrapLimit = 35; // Default for larger screens
    if (screenWidth < 400) {
        wrapLimit = 18; // Very small phones (iPhone SE, etc.)
    } else if (screenWidth < 576) {
        wrapLimit = 22; // Small phones
    } else if (screenWidth < 768) {
        wrapLimit = 28; // Larger phones / small tablets
    }

    // Create the chart with beautiful styling
    clubPollCharts[pollId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: filteredData.map(d => wrapLabel(d.label, wrapLimit)),
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
                        // Use smaller font on mobile for better fit
                        font: {
                            size: isMobile ? 11 : 13,
                            weight: '600'
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
    // Handle scroll to specific poll when URL has hash (e.g., #poll-123)
    if (window.location.hash) {
        const pollElement = document.querySelector(window.location.hash);
        if (pollElement) {
            // Small delay to ensure page is fully rendered
            setTimeout(function() {
                pollElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Add highlight effect
                pollElement.classList.add('poll-highlight');
                setTimeout(function() {
                    pollElement.classList.remove('poll-highlight');
                }, 2000);
            }, 100);
        }
    }

    // Get lakes data from data attribute
    const lakesDataElement = document.getElementById('lakes-data');
    const lakesData = lakesDataElement ? JSON.parse(lakesDataElement.dataset.lakes || '[]') : [];

    // Initialize poll voting handler
    const pollVotingHandler = new PollVotingHandler(lakesData);

    // Populate all lake dropdowns with options
    const allLakeSelects = document.querySelectorAll('select[data-poll-lake]');

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

    // Initialize tournament poll results renderer using shared PollResultsRenderer class
    pollResultsRenderer = new PollResultsRenderer({
        lakesData: lakesData,
        containerSelector: '.tournament-results-container',
        idAttribute: 'pollId'
    });
    pollResultsRenderer.renderAll();

    // Initialize club poll horizontal bar charts
    initializeClubPollCharts();

    // Re-render club poll charts on significant window resize (e.g., device rotation)
    // Use debounce to avoid excessive re-renders
    let resizeTimeout;
    let lastWidth = window.innerWidth;
    function handlePollsResize() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            const newWidth = window.innerWidth;
            // Only re-render if width changed significantly (crossing breakpoints)
            if ((lastWidth < 576 && newWidth >= 576) ||
                (lastWidth >= 576 && newWidth < 576) ||
                (lastWidth < 400 && newWidth >= 400) ||
                (lastWidth >= 400 && newWidth < 400) ||
                (lastWidth < 768 && newWidth >= 768) ||
                (lastWidth >= 768 && newWidth < 768)) {
                lastWidth = newWidth;
                initializeClubPollCharts();
            }
        }, 250);
    }
    window.addEventListener('resize', handlePollsResize);

    // Cleanup on page unload to prevent memory leaks
    window.addEventListener('beforeunload', function() {
        window.removeEventListener('resize', handlePollsResize);
        // Destroy all charts to free memory
        Object.values(clubPollCharts).forEach(function(chart) {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        clubPollCharts = {};
    });

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

/**
 * Trigger poll deletion confirmation modal
 * @param {number|string} pollId - Poll ID to delete
 * @param {string} pollTitle - Poll title for display in modal
 */
function deletePoll(pollId, pollTitle) {
    pollDeleteManager.confirm(pollId, pollTitle);
}
