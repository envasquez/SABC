/**
 * Home Page Poll Results Visualization
 *
 * This module handles the visualization of poll results for upcoming tournaments
 * on the home page using stacked bar charts showing lakes with ramp breakdown.
 */

// Global state for home page poll renderer
let homeResultsRenderer;

/**
 * Initialize home page poll visualization
 * @param {Object} config - Configuration object
 * @param {Array} config.lakesData - Array of lakes with ramps data
 */
function initializeHomePolls(config) {
    const lakesData = config.lakesData || [];

    // Initialize poll results renderer using shared PollResultsRenderer class
    homeResultsRenderer = new PollResultsRenderer({
        lakesData: lakesData,
        containerSelector: '.tournament-results-container-home',
        idAttribute: 'tournamentId'
    });
    homeResultsRenderer.renderAll();

    // Handle tab switching for pagination
    handleTabSwitching();
}

/**
 * Handle tab switching based on URL pagination parameter
 */
function handleTabSwitching() {
    const urlParams = new URLSearchParams(window.location.search);
    const pageParam = urlParams.get('p');

    // If there's a page parameter (pagination), switch to Completed tab
    if (pageParam) {
        const completedTab = document.getElementById('completed-tab');
        const upcomingTab = document.getElementById('upcoming-tab');
        const completedPane = document.getElementById('completed-pane');
        const upcomingPane = document.getElementById('upcoming-pane');

        if (completedTab && upcomingTab && completedPane && upcomingPane) {
            // Activate Completed tab
            completedTab.classList.add('active');
            completedTab.setAttribute('aria-selected', 'true');
            upcomingTab.classList.remove('active');
            upcomingTab.setAttribute('aria-selected', 'false');

            // Show Completed pane, hide Upcoming pane
            completedPane.classList.add('show', 'active');
            upcomingPane.classList.remove('show', 'active');
        }
    }
}

// Export functions to global scope for onclick handlers
window.initializeHomePolls = initializeHomePolls;
