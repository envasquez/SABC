/**
 * Enter Results page initialization JavaScript
 * Initializes the results entry form with data from data attributes
 */

(function() {
    'use strict';

document.addEventListener('DOMContentLoaded', function() {
    // Get results data from data attribute
    const resultsDataElement = document.getElementById('results-data');
    if (!resultsDataElement) {
        console.error('[SABC] Results data element not found');
        return;
    }

    const anglers = safeParseJSON(resultsDataElement.dataset.anglers, []);
    const existingAnglerIds = safeParseJSON(resultsDataElement.dataset.existingAnglerIds, []);
    const editData = safeParseJSON(resultsDataElement.dataset.editData, null);
    const editTeamResultData = safeParseJSON(resultsDataElement.dataset.editTeamResultData, null);
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

    // Bind Create Guest modal trigger and submit button (previously inline onclick)
    const showCreateGuestBtn = document.getElementById('showCreateGuestBtn');
    if (showCreateGuestBtn) {
        showCreateGuestBtn.addEventListener('click', showCreateGuestModal);
    }
    const createGuestBtn = document.getElementById('createGuestBtn');
    if (createGuestBtn) {
        createGuestBtn.addEventListener('click', createGuest);
    }
});
})();
