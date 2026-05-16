/**
 * SABC Admin Shared JavaScript Functions
 * Common utilities used across admin pages
 */

(function() {
    'use strict';

/**
 * Delete a poll vote by ID
 * @param {number} voteId - The ID of the vote to delete
 */
async function deleteVote(voteId) {
    try {
        const response = await deleteRequest(`/admin/votes/${voteId}`);
        if (!response.ok) throw new Error('Failed to delete vote');
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

// Delegated handlers for select-all / select-none checkbox controls and
// vote-delete buttons. Buttons may carry data-checkbox-name (default 'lake_ids');
// vote-delete buttons carry data-vote-id and data-voter-name.
document.addEventListener('click', function(e) {
    const allBtn = e.target.closest('.js-select-all');
    if (allBtn) {
        selectAll(allBtn.dataset.checkboxName || 'lake_ids');
        return;
    }
    const noneBtn = e.target.closest('.js-select-none');
    if (noneBtn) {
        selectNone(noneBtn.dataset.checkboxName || 'lake_ids');
        return;
    }
    const voteBtn = e.target.closest('.js-delete-vote');
    if (voteBtn) {
        const voterName = voteBtn.dataset.voterName || '';
        if (confirm('Delete vote by ' + voterName + '?')) {
            deleteVote(voteBtn.dataset.voteId);
        }
    }
});
})();
