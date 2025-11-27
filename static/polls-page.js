/**
 * Polls page JavaScript functionality
 * Initializes poll voting handler and delete confirmation manager
 */

// Initialize delete confirmation manager
let pollDeleteManager;
let pollResultsRenderer;

document.addEventListener('DOMContentLoaded', function() {
    console.log('[SABC] Polls page: DOMContentLoaded fired');

    // Get lakes data from data attribute
    const lakesDataElement = document.getElementById('lakes-data');
    const lakesData = lakesDataElement ? JSON.parse(lakesDataElement.dataset.lakes || '[]') : [];

    if (!lakesData || lakesData.length === 0) {
        console.warn('[SABC] Lakes data not loaded or empty');
    } else {
        console.log('[SABC] Lakes data loaded:', lakesData.length, 'lakes');
    }

    // Initialize poll voting handler
    const pollVotingHandler = new PollVotingHandler(lakesData);

    // Populate all lake dropdowns with options
    const allLakeSelects = document.querySelectorAll('select[data-poll-lake]');
    console.log('[SABC] Found', allLakeSelects.length, 'lake select dropdowns');

    allLakeSelects.forEach(lakeSelect => {
        lakesData.forEach(lake => {
            const option = document.createElement('option');
            option.value = lake.id;
            option.textContent = lake.name;
            lakeSelect.appendChild(option);
        });
    });

    // Initialize the poll voting handler (sets up all event listeners)
    pollVotingHandler.initialize();

    console.log('[SABC] Poll voting handler initialized successfully');

    // Initialize poll results renderer using shared PollResultsRenderer class
    pollResultsRenderer = new PollResultsRenderer({
        lakesData: lakesData,
        containerSelector: '.tournament-results-container',
        idAttribute: 'pollId'
    });
    pollResultsRenderer.renderAll();

    // Initialize delete confirmation manager
    pollDeleteManager = new DeleteConfirmationManager({
        modalId: 'deletePollModal',
        itemNameElementId: 'deletePollTitle',
        confirmInputId: 'deletePollConfirmInput',
        confirmButtonId: 'confirmDeletePollBtn',
        deleteUrlTemplate: (id) => `/admin/polls/${id}`,
        onSuccess: () => location.reload(),
        onError: (error) => showToast(`Error deleting poll: ${error}`, 'error')
    });
});

function deletePoll(pollId, pollTitle) {
    pollDeleteManager.confirm(pollId, pollTitle);
}

// Expose selectLakePoll to global scope for backward compatibility
window.selectLakePoll = function(pollId, lakeId) {
    if (pollResultsRenderer) {
        pollResultsRenderer.selectLake(pollId, lakeId);
    }
};
