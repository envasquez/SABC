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
        // Get CSRF token from cookie
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrf_token='))
            ?.split('=')[1];

        const response = await fetch(`/admin/votes/${voteId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'x-csrf-token': csrfToken,
            }
        });

        const result = await response.json();

        if (result.success) {
            // Show success message and reload page
            alert('Vote deleted successfully: ' + result.message);
            location.reload();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error deleting vote: ' + error.message);
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
