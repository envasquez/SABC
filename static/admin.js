/**
 * SABC Admin Shared JavaScript Functions
 * Common utilities used across admin pages
 */

/**
 * Delete a poll vote by ID
 * @param {number} voteId - The ID of the vote to delete
 */
async function deleteVote(voteId) {
    try {
        const response = await deleteRequest(`/admin/votes/${voteId}`);
        const result = await response.json();

        if (result.success) {
            // Show success message and reload page
            showToast('Vote deleted successfully: ' + result.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error deleting vote: ' + error.message, 'error');
    }
}

/**
 * Select all checkboxes with a given name
 * @param {string} checkboxName - The name attribute of checkboxes to select (default: 'lake_ids')
 */
function selectAll(checkboxName = 'lake_ids') {
    document.querySelectorAll(`input[name="${checkboxName}"]`).forEach(checkbox => {
        checkbox.checked = true;
    });
}

/**
 * Deselect all checkboxes with a given name
 * @param {string} checkboxName - The name attribute of checkboxes to deselect (default: 'lake_ids')
 */
function selectNone(checkboxName = 'lake_ids') {
    document.querySelectorAll(`input[name="${checkboxName}"]`).forEach(checkbox => {
        checkbox.checked = false;
    });
}
