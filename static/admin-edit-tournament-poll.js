/**
 * Admin Edit Tournament Poll page JavaScript functionality
 * Handles lake selection for tournament polls
 */

function selectAllLakes() {
    document.querySelectorAll('.lake-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
}

function deselectAllLakes() {
    document.querySelectorAll('.lake-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
}
