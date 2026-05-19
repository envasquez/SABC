/**
 * Roster page JavaScript functionality
 * Handles expandable member rows and weight chart rendering
 */

(function() {
    'use strict';

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

        // Tooltip label callback that accounts for buy-in entries
        const buyInTooltipLabel = function(context) {
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
        };

        // Start from the shared line-chart options, then apply roster-specific styling
        const options = lineChartOptions({
            maintainAspectRatio: false,
            tooltipLabel: buyInTooltipLabel
        });

        // Roster-specific legend styling
        options.plugins.legend.labels.font = { size: 11 };
        options.plugins.legend.labels.boxWidth = 12;
        options.plugins.legend.labels.padding = 10;

        // Roster-specific tooltip styling (dark themed)
        options.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
        options.plugins.tooltip.titleColor = '#fff';
        options.plugins.tooltip.bodyColor = '#e2e8f0';
        options.plugins.tooltip.padding = 10;
        options.plugins.tooltip.cornerRadius = 6;

        // Roster-specific axis tick styling
        options.scales.y.ticks.color = '#94a3b8';
        options.scales.y.ticks.font = { size: 10 };
        options.scales.y.grid.color = 'rgba(148, 163, 184, 0.15)';
        options.scales.x.ticks.color = '#94a3b8';
        options.scales.x.ticks.font = { size: 10 };
        options.scales.x.grid.color = 'rgba(148, 163, 184, 0.1)';

        const ctx = chartCanvas.getContext('2d');
        memberCharts[memberId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: datasets
            },
            options: options
        });
    }

    /**
     * Toggle chart row visibility — no Bootstrap collapse, no animation, no ResizeObserver issues
     */
    function toggleChartRow(memberId) {
        const chartRow = document.getElementById('chart-row-' + memberId);
        if (!chartRow) return;
        const memberRow = chartRow.previousElementSibling;
        const icon = memberRow ? memberRow.querySelector('.expand-icon') : null;

        if (chartRow.style.display === 'none') {
            // Show
            chartRow.style.display = 'table-row';
            if (icon) {
                icon.classList.remove('bi-bar-chart-line');
                icon.classList.add('bi-bar-chart-line-fill');
                icon.style.color = 'var(--ok)';
            }
            // Init chart after row is visible and laid out
            requestAnimationFrame(function() {
                initMemberChart(memberId);
            });
        } else {
            // Hide
            chartRow.style.display = 'none';
            if (icon) {
                icon.classList.remove('bi-bar-chart-line-fill');
                icon.classList.add('bi-bar-chart-line');
                icon.style.color = 'var(--brand)';
            }
        }
    }

    // Delegated handler for expanding/collapsing a member's stats row
    document.addEventListener('DOMContentLoaded', function() {
        document.addEventListener('click', function(e) {
            const row = e.target.closest('.member-row');
            if (row && row.dataset.memberId) {
                toggleChartRow(row.dataset.memberId);
            }
        });
    });
})();
