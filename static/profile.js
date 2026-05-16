/**
 * Profile page JavaScript functionality
 * Handles profile editing, account deletion, and chart rendering
 */

(function() {
    'use strict';

    // Profile edit toggle functions.
    // The Edit button toggles between view/edit; its label reflects current mode.
    function isEditing() {
        const editMode = document.getElementById('editMode');
        return editMode && editMode.style.display === 'block';
    }

    function toggleEditMode() {
        if (isEditing()) {
            cancelEdit();
        } else {
            toggleEdit();
        }
    }

    function toggleEdit() {
        const viewMode = document.getElementById('viewMode');
        const editMode = document.getElementById('editMode');
        const editBtn = document.getElementById('editBtn');
        if (viewMode) viewMode.style.display = 'none';
        if (editMode) editMode.style.display = 'block';
        if (editBtn) {
            editBtn.innerHTML = '<i class="bi bi-eye me-1"></i>View';
        }
    }

    function cancelEdit() {
        const viewMode = document.getElementById('viewMode');
        const editMode = document.getElementById('editMode');
        const editBtn = document.getElementById('editBtn');
        if (viewMode) viewMode.style.display = 'block';
        if (editMode) editMode.style.display = 'none';
        if (editBtn) {
            editBtn.innerHTML = '<i class="bi bi-pencil me-1"></i>Edit';
        }
    }

    function startDeleteProcess() {
        showModal('deleteModal');
    }

    // Initialize profile page functionality
    document.addEventListener('DOMContentLoaded', function() {
        // Edit / cancel / delete buttons (previously inline onclick handlers)
        const editBtn = document.getElementById('editBtn');
        if (editBtn) editBtn.addEventListener('click', toggleEditMode);
        const cancelEditBtn = document.getElementById('cancelEditBtn');
        if (cancelEditBtn) cancelEditBtn.addEventListener('click', cancelEdit);
        const startDeleteBtn = document.getElementById('startDeleteBtn');
        if (startDeleteBtn) startDeleteBtn.addEventListener('click', startDeleteProcess);

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

        // Get data from the hidden data element
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
            // Shared line-chart options from utils.js (with axis titles)
            options: lineChartOptions({ maintainAspectRatio: true, axisTitles: true })
        });
    }

})();
