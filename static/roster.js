/**
 * Roster page JavaScript functionality
 * Handles expandable member rows and weight chart rendering
 */

// Store chart instances to avoid duplicates
const memberCharts = {};

/**
 * Initialize a weight chart for a specific member
 * @param {string} memberId - The member's ID
 */
function initMemberChart(memberId) {
    // Don't recreate if already exists
    if (memberCharts[memberId]) {
        return;
    }

    const chartCanvas = document.getElementById('chart-' + memberId);
    if (!chartCanvas) return;

    // Get data from the hidden data element
    const chartRow = chartCanvas.closest('.chart-row');
    const dataElement = chartRow.querySelector('.chart-data');
    if (!dataElement) return;

    const monthlyData = JSON.parse(dataElement.dataset.monthlyData || '{}');

    // Check if there's any data
    const hasData = Object.values(monthlyData).some(yearData =>
        yearData.some(val => val > 0)
    );

    if (!hasData) {
        // Show "no data" message instead of empty chart
        const container = chartCanvas.parentElement;
        container.innerHTML = `
            <div class="text-center py-4 text-muted">
                <i class="bi bi-inbox" style="font-size: 2rem; opacity: 0.5;"></i>
                <p class="mt-2 mb-0">No tournament data available</p>
            </div>`;
        return;
    }

    // Generate datasets for each year
    const datasets = [];
    const colors = [
        { border: 'rgb(54, 162, 235)', bg: 'rgba(54, 162, 235, 0.1)' },    // Blue
        { border: 'rgb(75, 192, 192)', bg: 'rgba(75, 192, 192, 0.1)' },    // Teal
        { border: 'rgb(255, 205, 86)', bg: 'rgba(255, 205, 86, 0.1)' },    // Gold
        { border: 'rgb(255, 99, 132)', bg: 'rgba(255, 99, 132, 0.1)' },    // Red
        { border: 'rgb(153, 102, 255)', bg: 'rgba(153, 102, 255, 0.1)' },  // Purple
    ];

    const years = Object.keys(monthlyData).sort();
    years.forEach((year, index) => {
        const colorIndex = index % colors.length;
        datasets.push({
            label: year,
            data: monthlyData[year],
            borderColor: colors[colorIndex].border,
            backgroundColor: colors[colorIndex].bg,
            tension: 0.3,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 5
        });
    });

    const ctx = chartCanvas.getContext('2d');
    memberCharts[memberId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#ffffff',
                        font: { size: 11 },
                        boxWidth: 12,
                        padding: 10
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#e2e8f0',
                    padding: 10,
                    cornerRadius: 6,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null && context.parsed.y > 0) {
                                label += context.parsed.y.toFixed(2) + ' lbs';
                            } else {
                                label += '0 lbs';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 10 },
                        callback: function(value) {
                            return value + ' lbs';
                        }
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.15)'
                    }
                },
                x: {
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 10 }
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

/**
 * Handle row expand/collapse icon and visual feedback
 */
function setupExpandIcons() {
    document.querySelectorAll('.member-row').forEach(row => {
        const targetId = row.dataset.bsTarget;
        const chartRow = document.querySelector(targetId);
        const icon = row.querySelector('.expand-icon');

        if (chartRow && icon) {
            // Listen for Bootstrap collapse events
            chartRow.addEventListener('show.bs.collapse', function() {
                // Change to filled chart icon and highlight
                icon.classList.remove('bi-bar-chart-line', 'text-primary');
                icon.classList.add('bi-bar-chart-line-fill', 'text-success');
                row.classList.add('table-active');
                // Initialize chart when row expands
                const memberId = targetId.replace('#chart-row-', '');
                initMemberChart(memberId);
            });

            chartRow.addEventListener('hide.bs.collapse', function() {
                // Revert to outline chart icon
                icon.classList.remove('bi-bar-chart-line-fill', 'text-success');
                icon.classList.add('bi-bar-chart-line', 'text-primary');
                row.classList.remove('table-active');
            });
        }

        // Add hover effect
        row.addEventListener('mouseenter', function() {
            if (!chartRow || !chartRow.classList.contains('show')) {
                this.style.backgroundColor = 'rgba(13, 110, 253, 0.1)';
            }
        });
        row.addEventListener('mouseleave', function() {
            if (!chartRow || !chartRow.classList.contains('show')) {
                this.style.backgroundColor = '';
            }
        });
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[SABC] Roster page: Initializing weight charts');
    setupExpandIcons();
});
