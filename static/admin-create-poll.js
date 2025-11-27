/**
 * Admin Create Poll page JavaScript functionality
 * Initializes poll timing and remove buttons
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get event date from data attribute
    const pollDataElement = document.getElementById('poll-data');
    const eventDate = pollDataElement ? pollDataElement.dataset.eventDate : '';

    // Set dates for tournament poll
    setOptimalPollTiming(eventDate, 'starts_at', 'closes_at');

    // Set dates for generic poll
    setOptimalPollTiming(eventDate, 'generic_starts_at', 'generic_closes_at');

    // Initialize remove button states
    updateRemoveButtons();
});
