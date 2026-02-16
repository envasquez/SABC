/**
 * Roster page JavaScript functionality
 * Handles expandable member rows and weight chart rendering
 */

// Store chart instances to avoid duplicates
const memberCharts = {};

/**
 * Custom plugin to draw dollar signs for buy-in points
 */
const dollarSignPlugin = {
    id: 'dollarSignPlugin',
    afterDatasetsDraw: function(chart) {
        const ctx = chart.ctx;
        chart.data.datasets.forEach((dataset, datasetIndex) => {
            if (!dataset.buyInData) return;

            const meta = chart.getDatasetMeta(datasetIndex);
            meta.data.forEach((point, index) => {
                const buyIn = dataset.buyInData[index];
                const weight = dataset.data[index];

                // Show $ for zero weight with buy-in
                if (buyIn && weight === 0) {
                    ctx.save();
                    ctx.font = 'bold 14px Arial';
                    ctx.fillStyle = '#ffc107'; // Bootstrap warning yellow
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('$', point.x, point.y - 12);
                    ctx.restore();
                }
            });
        });
    }
};

// Register the plugin
Chart.register(dollarSignPlugin);

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

    // Check if there's any data - handle both old format (numbers) and new format (objects)
    const hasData = Object.values(monthlyData).some(yearData =>
        yearData.some(val => {
            if (typeof val === 'object' && val !== null) {
                return val.weight > 0 || val.buy_in;
            }
            return val > 0;
        })
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

    // Generate datasets for each year using shared color palette
    const datasets = [];
    const years = Object.keys(monthlyData).sort();
    years.forEach((year, index) => {
        const color = CHART_LINE_COLORS[index % CHART_LINE_COLORS.length];
        const yearData = monthlyData[year];

        // Extract weights and buy_in flags from the new format
        const weights = yearData.map(item => {
            if (typeof item === 'object' && item !== null) {
                return item.weight || 0;
            }
            return item || 0;
        });

        const buyInFlags = yearData.map(item => {
            if (typeof item === 'object' && item !== null) {
                return item.buy_in || false;
            }
            return false;
        });

        datasets.push({
            label: year,
            data: weights,
            buyInData: buyInFlags, // Custom property for the plugin
            borderColor: color.border,
            backgroundColor: color.bg,
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
                            const buyIn = context.dataset.buyInData && context.dataset.buyInData[context.dataIndex];
                            if (context.parsed.y !== null && context.parsed.y > 0) {
                                label += context.parsed.y.toFixed(2) + ' lbs';
                            } else if (buyIn) {
                                label += '0 lbs (buy-in)';
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
    setupExpandIcons();
});
