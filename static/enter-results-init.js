/**
 * Enter Results page initialization JavaScript
 * Initializes the results entry form with data from data attributes
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get results data from data attribute
    const resultsDataElement = document.getElementById('results-data');
    if (!resultsDataElement) {
        console.error('[SABC] Results data element not found');
        return;
    }

    const anglers = JSON.parse(resultsDataElement.dataset.anglers || '[]');
    const existingAnglerIds = JSON.parse(resultsDataElement.dataset.existingAnglerIds || '[]');
    const editData = resultsDataElement.dataset.editData ?
        JSON.parse(resultsDataElement.dataset.editData) : null;
    const editTeamResultData = resultsDataElement.dataset.editTeamResultData ?
        JSON.parse(resultsDataElement.dataset.editTeamResultData) : null;
    const tournamentId = parseInt(resultsDataElement.dataset.tournamentId, 10);
    const isTeamFormat = resultsDataElement.dataset.isTeamFormat === 'true';

    // Initialize results entry with the data
    initializeResultsEntry({
        anglers: anglers,
        existingAnglerIds: existingAnglerIds,
        editData: editData,
        editTeamResultData: editTeamResultData,
        tournamentId: tournamentId,
        isTeamFormat: isTeamFormat
    });
});
