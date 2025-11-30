/**
 * Profile page JavaScript functionality
 * Handles profile editing, account deletion, and chart rendering
 */

// Profile edit toggle functions
function toggleEdit() {
    document.getElementById('viewMode').style.display = 'none';
    document.getElementById('editMode').style.display = 'block';
    document.getElementById('editBtn').innerHTML = '<i class="bi bi-eye me-1"></i>View';
    document.getElementById('editBtn').onclick = cancelEdit;
}

function cancelEdit() {
    document.getElementById('viewMode').style.display = 'block';
    document.getElementById('editMode').style.display = 'none';
    document.getElementById('editBtn').innerHTML = '<i class="bi bi-pencil me-1"></i>Edit';
    document.getElementById('editBtn').onclick = toggleEdit;
}

function startDeleteProcess() {
    showModal('deleteModal');
}

// Initialize profile page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Delete confirmation input handler
    const deleteConfirm = document.getElementById('deleteConfirm');
    if (deleteConfirm) {
        deleteConfirm.addEventListener('input', function(e) {
            const btn = document.getElementById('deleteSubmitBtn');
            btn.disabled = e.target.value !== 'DELETE';
        });
    }

    // Phone number formatting
    const phoneInput = document.getElementById('phoneInput');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, ''); // Remove all non-digits

            if (value.length === 0) {
                e.target.value = '';
                return;
            }

            // Remove leading 1 if present
            if (value.length === 11 && value[0] === '1') {
                value = value.substring(1);
            }

            // Format the number as (XXX) XXX-XXXX
            if (value.length <= 3) {
                e.target.value = '(' + value;
            } else if (value.length <= 6) {
                e.target.value = '(' + value.substring(0, 3) + ') ' + value.substring(3);
            } else if (value.length <= 10) {
                e.target.value = '(' + value.substring(0, 3) + ') ' + value.substring(3, 6) + '-' + value.substring(6);
            } else {
                // Don't allow more than 10 digits
                e.target.value = '(' + value.substring(0, 3) + ') ' + value.substring(3, 6) + '-' + value.substring(6, 10);
            }
        });

        // Also format on blur to ensure consistency
        phoneInput.addEventListener('blur', function(e) {
            let value = e.target.value.replace(/\D/g, '');

            if (value.length === 10) {
                e.target.value = '(' + value.substring(0, 3) + ') ' + value.substring(3, 6) + '-' + value.substring(6);
            } else if (value.length === 0) {
                e.target.value = '';
            }
        });
    }

    // Initialize monthly weight chart if element exists
    initMonthlyWeightChart();
});

/**
 * Initialize the monthly weight chart
 * Reads data from data-monthly-data attribute on chart container
 */
function initMonthlyWeightChart() {
    const chartCanvas = document.getElementById('monthlyWeightChart');
    if (!chartCanvas) return;

    // Get data from parent element's data attribute
    const chartContainer = chartCanvas.closest('.card-body');
    const dataElement = document.getElementById('chart-data');
    if (!dataElement) return;

    const monthlyData = JSON.parse(dataElement.dataset.monthlyData || '{}');

    // Generate dynamic datasets for each year using shared color palette
    const datasets = [];
    const years = Object.keys(monthlyData).sort();
    years.forEach((year, index) => {
        const color = CHART_LINE_COLORS[index % CHART_LINE_COLORS.length];
        datasets.push({
            label: year,
            data: monthlyData[year],
            borderColor: color.border,
            backgroundColor: color.bg,
            tension: 0.3,
            fill: true
        });
    });

    const ctx = chartCanvas.getContext('2d');
    new Chart(ctx, {
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
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(2) + ' lbs';
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
                        color: '#ffffff',
                        callback: function(value) {
                            return value + ' lbs';
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Total Weight (lbs)',
                        color: '#ffffff'
                    }
                },
                x: {
                    ticks: {
                        color: '#ffffff'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Month',
                        color: '#ffffff'
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
