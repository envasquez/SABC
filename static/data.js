/**
 * Club Data Dashboard page JavaScript
 * Builds all Chart.js visualizations from server-provided JSON.
 *
 * Data is read from the #data-dashboard element's data-* attributes
 * (populated server-side in templates/data.html).
 */

(function() {
    'use strict';

    // Store chart data (populated on DOMContentLoaded from the data element)
    let originalData = {};

    // Chart instances
    const charts = {};

    // Store participation data grouped by year for tooltip access
    let participationByYear = {};

    // Initialize all charts
    function initCharts(data) {
        // Use all data (no filtering)
        const filteredLimitsZeros = data.limitsZerosByYear;

        // Initialize participation chart (stacked by year)
        initParticipationChart();

        // Limits vs Zeros
        if (charts.limitsZeros) charts.limitsZeros.destroy();
        charts.limitsZeros = new Chart(document.getElementById('limitsZerosChart'), {
            type: 'bar',
            plugins: [ChartDataLabels],
            data: {
                labels: filteredLimitsZeros.map(d => d.year),
                datasets: [
                    {
                        label: 'Limits',
                        data: filteredLimitsZeros.map(d => d.limits),
                        backgroundColor: '#198754'
                    },
                    {
                        label: 'Zeros',
                        data: filteredLimitsZeros.map(d => d.zeros),
                        backgroundColor: '#dc3545'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    datalabels: {
                        display: function(context) {
                            return context.dataset.data[context.dataIndex] > 0;
                        },
                        anchor: 'center',
                        align: 'center',
                        color: '#fff',
                        font: { weight: 'bold', size: 10 }
                    }
                },
                scales: { y: { beginAtZero: true } }
            }
        });

        // Winning Weights by Year (Stacked bar: 3rd on bottom, 1st on top)
        const filteredWinningByYear = data.winningWeightsByYear;
        if (charts.winningByYear) charts.winningByYear.destroy();
        charts.winningByYear = new Chart(document.getElementById('winningWeightsByYearChart'), {
            type: 'bar',
            plugins: [ChartDataLabels],
            data: {
                labels: filteredWinningByYear.map(d => d.year),
                datasets: [
                    {
                        label: '3rd Place',
                        data: filteredWinningByYear.map(d => d.avg_3rd ? d.avg_3rd.toFixed(2) : 0),
                        backgroundColor: '#cd7f32'
                    },
                    {
                        label: '2nd Place',
                        data: filteredWinningByYear.map(d => d.avg_2nd ? d.avg_2nd.toFixed(2) : 0),
                        backgroundColor: '#6c757d'
                    },
                    {
                        label: '1st Place',
                        data: filteredWinningByYear.map(d => d.avg_1st ? d.avg_1st.toFixed(2) : 0),
                        backgroundColor: '#ffc107'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', reverse: true },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + ' lbs';
                            }
                        }
                    },
                    datalabels: {
                        display: function(context) {
                            return parseFloat(context.dataset.data[context.dataIndex]) > 0;
                        },
                        anchor: 'center',
                        align: 'center',
                        color: function(context) {
                            // Use dark text on yellow (1st place), white on others
                            return context.datasetIndex === 2 ? '#000' : '#fff';
                        },
                        font: { weight: 'bold', size: 9 },
                        formatter: function(value) {
                            return parseFloat(value).toFixed(1);
                        }
                    }
                },
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Weight (lbs)' } }
                }
            }
        });

        // Initialize the combined lake chart starting with "All Years"
        initLakeChart('all');
    }

    // Initialize Participation chart as stacked area by year
    function initParticipationChart() {
        const data = originalData.tournamentParticipation;

        // Get unique years and sort them
        const years = [...new Set(data.map(d => d.year))].sort();

        // Find max tournaments in any year to determine x-axis labels
        const tournamentsByYear = {};
        years.forEach(year => {
            tournamentsByYear[year] = data.filter(d => d.year === year);
        });
        const maxTournaments = Math.max(...years.map(y => tournamentsByYear[y].length));

        // Create labels (Tournament 1, Tournament 2, etc.)
        const labels = Array.from({length: maxTournaments}, (_, i) => `T${i + 1}`);

        // Store for tooltip access
        participationByYear = tournamentsByYear;

        // Color palette for years
        const colors = [
            { border: '#0d6efd', bg: 'rgba(13, 110, 253, 0.5)' },   // blue
            { border: '#198754', bg: 'rgba(25, 135, 84, 0.5)' },    // green
            { border: '#ffc107', bg: 'rgba(255, 193, 7, 0.5)' },    // yellow
            { border: '#dc3545', bg: 'rgba(220, 53, 69, 0.5)' },    // red
            { border: '#6f42c1', bg: 'rgba(111, 66, 193, 0.5)' },   // purple
            { border: '#20c997', bg: 'rgba(32, 201, 151, 0.5)' },   // teal
            { border: '#fd7e14', bg: 'rgba(253, 126, 20, 0.5)' },   // orange
            { border: '#6c757d', bg: 'rgba(108, 117, 125, 0.5)' },  // gray
            { border: '#0dcaf0', bg: 'rgba(13, 202, 240, 0.5)' },   // cyan
            { border: '#d63384', bg: 'rgba(214, 51, 132, 0.5)' }    // pink
        ];

        // Create datasets for each year
        const currentYear = new Date().getFullYear();
        const datasets = years.map((year, idx) => {
            const yearData = tournamentsByYear[year];
            const participantCounts = yearData.map(d => d.participants);
            // Pad with nulls if this year has fewer tournaments
            while (participantCounts.length < maxTournaments) {
                participantCounts.push(null);
            }
            const color = colors[idx % colors.length];
            const isCurrentYear = year === currentYear;
            return {
                label: year.toString(),
                data: participantCounts,
                borderColor: color.border,
                backgroundColor: color.bg,
                fill: isCurrentYear,
                tension: 0.3,
                pointRadius: isCurrentYear ? 5 : 4,
                pointHoverRadius: 6,
                borderWidth: isCurrentYear ? 3 : 2,
                spanGaps: false
            };
        });

        if (charts.membershipParticipation) charts.membershipParticipation.destroy();
        charts.membershipParticipation = new Chart(document.getElementById('membershipParticipationChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return 'Tournament ' + (context[0].dataIndex + 1);
                            },
                            label: function(context) {
                                const year = parseInt(context.dataset.label);
                                const idx = context.dataIndex;
                                const yearData = participationByYear[year];
                                if (!yearData || !yearData[idx]) return null;
                                const t = yearData[idx];
                                return `${year}: ${t.participants} (${t.lake_name})`;
                            },
                            afterLabel: function(context) {
                                const year = parseInt(context.dataset.label);
                                const idx = context.dataIndex;
                                const yearData = participationByYear[year];
                                if (!yearData || !yearData[idx]) return null;
                                const t = yearData[idx];
                                return `  Members: ${t.members}, Guests: ${t.guests}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: false,
                        title: { display: true, text: 'Tournament Number' }
                    },
                    y: {
                        stacked: false,
                        beginAtZero: true,
                        title: { display: true, text: 'Participants' }
                    }
                }
            }
        });
    }

    // Initialize combined Lake chart (All Years or specific year)
    function initLakeChart(yearOrAll) {
        const isAllYears = yearOrAll === 'all';

        // Update the badge
        document.getElementById('selectedYearBadge').textContent = isAllYears ? 'All Years' : yearOrAll;

        let chartData, datasets;

        if (isAllYears) {
            // All Years: Show 1st/2nd/3rd stacked bars + tournament count (line)
            chartData = originalData.winningWeightsByLake;
            // Sort by avg_1st descending
            chartData.sort((a, b) => (b.avg_1st || 0) - (a.avg_1st || 0));

            datasets = [
                {
                    label: '3rd Place',
                    data: chartData.map(d => d.avg_3rd ? d.avg_3rd.toFixed(2) : 0),
                    backgroundColor: '#cd7f32',
                    yAxisID: 'y',
                    stack: 'Stack 0',
                    order: 2
                },
                {
                    label: '2nd Place',
                    data: chartData.map(d => d.avg_2nd ? d.avg_2nd.toFixed(2) : 0),
                    backgroundColor: '#6c757d',
                    yAxisID: 'y',
                    stack: 'Stack 0',
                    order: 2
                },
                {
                    label: '1st Place',
                    data: chartData.map(d => d.avg_1st ? d.avg_1st.toFixed(2) : 0),
                    backgroundColor: '#ffc107',
                    yAxisID: 'y',
                    stack: 'Stack 0',
                    order: 2
                },
                {
                    label: 'Tournament Count',
                    data: chartData.map(d => d.tournament_count),
                    type: 'line',
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointBackgroundColor: '#dc3545',
                    yAxisID: 'y1',
                    fill: false,
                    tension: 0.4,
                    order: 0
                }
            ];
        } else {
            // Specific year: Show 1st/2nd/3rd stacked bars + tournament count (line)
            chartData = originalData.winningWeightsByLakeYear.filter(d => d.year === yearOrAll);
            // Sort by avg_1st descending
            chartData.sort((a, b) => (b.avg_1st || 0) - (a.avg_1st || 0));

            datasets = [
                {
                    label: '3rd Place',
                    data: chartData.map(d => d.avg_3rd ? d.avg_3rd.toFixed(2) : 0),
                    backgroundColor: '#cd7f32',
                    yAxisID: 'y',
                    stack: 'Stack 0',
                    order: 2
                },
                {
                    label: '2nd Place',
                    data: chartData.map(d => d.avg_2nd ? d.avg_2nd.toFixed(2) : 0),
                    backgroundColor: '#6c757d',
                    yAxisID: 'y',
                    stack: 'Stack 0',
                    order: 2
                },
                {
                    label: '1st Place',
                    data: chartData.map(d => d.avg_1st ? d.avg_1st.toFixed(2) : 0),
                    backgroundColor: '#ffc107',
                    yAxisID: 'y',
                    stack: 'Stack 0',
                    order: 2
                },
                {
                    label: 'Tournament Count',
                    data: chartData.map(d => d.tournament_count),
                    type: 'line',
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointBackgroundColor: '#dc3545',
                    yAxisID: 'y1',
                    fill: false,
                    tension: 0.4,
                    order: 0
                }
            ];
        }

        if (charts.winningByLake) charts.winningByLake.destroy();
        charts.winningByLake = new Chart(document.getElementById('winningWeightsByLakeChart'), {
            type: 'bar',
            plugins: [ChartDataLabels],
            data: {
                labels: chartData.map(d => d.lake_name),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        reverse: true
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.dataset.label.includes('Count')) {
                                    return context.dataset.label + ': ' + context.parsed.y;
                                }
                                return context.dataset.label + ': ' + context.parsed.y + ' lbs';
                            }
                        }
                    },
                    datalabels: {
                        display: function(context) {
                            // Only show labels for bar datasets (not the line), and only if value > 0
                            return context.dataset.type !== 'line' && parseFloat(context.dataset.data[context.dataIndex]) > 0;
                        },
                        anchor: 'center',
                        align: 'center',
                        color: function(context) {
                            // Dark text on yellow (1st place), white on others
                            return context.dataset.label === '1st Place' ? '#000' : '#fff';
                        },
                        font: { weight: 'bold', size: 9 },
                        formatter: function(value) {
                            return parseFloat(value).toFixed(1);
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        stacked: true,
                        beginAtZero: true,
                        title: { display: true, text: 'Weight (lbs)' }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        title: { display: true, text: 'Tournament Count' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        const dataEl = document.getElementById('data-dashboard');
        if (!dataEl) return;

        originalData = {
            weightTrends: JSON.parse(dataEl.dataset.weightTrends || '[]'),
            membershipByYear: JSON.parse(dataEl.dataset.membershipByYear || '[]'),
            limitsZerosByYear: JSON.parse(dataEl.dataset.limitsZerosByYear || '[]'),
            winningWeightsByYear: JSON.parse(dataEl.dataset.winningWeightsByYear || '[]'),
            winningWeightsByLake: JSON.parse(dataEl.dataset.winningWeightsByLake || '[]'),
            winningWeightsByLakeYear: JSON.parse(dataEl.dataset.winningWeightsByLakeYear || '[]'),
            tournamentParticipation: JSON.parse(dataEl.dataset.tournamentParticipation || '[]'),
            ytdTrends: JSON.parse(dataEl.dataset.ytdTrends || '[]')
        };

        initCharts(originalData);

        // Set up lake year tab click handlers
        document.querySelectorAll('.lake-year-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                // Update active state
                document.querySelectorAll('.lake-year-btn').forEach(b => b.classList.remove('on'));
                this.classList.add('on');

                // Render chart for selected year or all years
                const yearValue = this.dataset.year;
                initLakeChart(yearValue === 'all' ? 'all' : parseInt(yearValue));
            });
        });
    });
})();
