/**
 * Tournament Results page JavaScript functionality
 * Handles result deletion operations for individual, team, and buy-in results
 */

async function deleteIndividualResult(tournamentId, resultId, anglerName) {
    if (confirm(`Are you sure you want to delete the result for ${anglerName}?\n\nThis will also delete any team results that include this angler.\n\nThis action cannot be undone.`)) {
        try {
            const response = await deleteRequest(`/admin/tournaments/${tournamentId}/results/${resultId}`);

            if (response.ok) {
                window.location.reload();
            } else {
                const text = await response.text();
                try {
                    const data = JSON.parse(text);
                    showToast(data.error || 'Error deleting result. Please try again.', 'error');
                } catch(e) {
                    showToast('Error deleting result: ' + text, 'error');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error deleting result. Please try again.', 'error');
        }
    }
}

async function deleteBuyInResult(tournamentId, resultId, anglerName) {
    if (confirm(`Are you sure you want to delete the buy-in result for ${anglerName}?\n\nThis action cannot be undone.`)) {
        try {
            const response = await deleteRequest(`/admin/tournaments/${tournamentId}/results/${resultId}`);

            if (response.ok) {
                window.location.reload();
            } else {
                const text = await response.text();
                try {
                    const data = JSON.parse(text);
                    showToast(data.error || 'Error deleting buy-in result. Please try again.', 'error');
                } catch(e) {
                    showToast('Error deleting buy-in result: ' + text, 'error');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error deleting buy-in result. Please try again.', 'error');
        }
    }
}

async function deleteTeamResult(tournamentId, teamResultId, teamName, isSolo) {
    const memberText = isSolo ? 'this angler' : 'both team members';
    if (confirm(`Are you sure you want to delete the team result for ${teamName}?\n\nThis will also delete the individual results for ${memberText}.\n\nThis action cannot be undone.`)) {
        try {
            const response = await deleteRequest(`/admin/tournaments/${tournamentId}/team-results/${teamResultId}`);

            if (response.ok) {
                window.location.reload();
            } else {
                const text = await response.text();
                try {
                    const data = JSON.parse(text);
                    showToast(data.error || 'Error deleting team result. Please try again.', 'error');
                } catch(e) {
                    showToast('Error deleting team result: ' + text, 'error');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error deleting team result. Please try again.', 'error');
        }
    }
}
