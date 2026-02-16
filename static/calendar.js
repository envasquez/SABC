/**
 * Calendar page JavaScript functionality
 * Handles event details modal display
 */

// Event data will be populated from data attributes
let currentEventDetails = {};
let nextEventDetails = {};
let currentYear = '';

document.addEventListener('DOMContentLoaded', function() {
    // Get calendar data from data attribute
    const calendarDataElement = document.getElementById('calendar-data');
    if (calendarDataElement) {
        currentEventDetails = JSON.parse(calendarDataElement.dataset.currentEvents || '{}');
        nextEventDetails = JSON.parse(calendarDataElement.dataset.nextEvents || '{}');
        currentYear = calendarDataElement.dataset.currentYear || '';
    }
});

function showEventDetails(element) {
    const year = element.getAttribute('data-year');
    const month = element.getAttribute('data-month');
    const day = element.getAttribute('data-day');
    const eventKey = month + '-' + day;

    // Select the appropriate event details based on year
    const eventDetails = (year == currentYear) ? currentEventDetails : nextEventDetails;

    if (eventDetails[eventKey]) {
        const events = eventDetails[eventKey];
        const eventDate = events[0].date;
        const dateObj = new Date(eventDate + 'T00:00:00');
        const formattedDate = dateObj.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });

        // Set modal title (using textContent for safe text)
        document.getElementById('eventModalTitle').textContent = formattedDate;

        // Build modal body content
        let modalContent = '';
        events.forEach(function(event, index) {
            let eventTypeIcon = '';
            let eventTypeName = '';
            let eventTypeClass = '';

            if (event.type === 'holiday') {
                eventTypeIcon = '<i class="bi bi-calendar-x me-2"></i>';
                eventTypeName = 'Federal Holiday';
                eventTypeClass = 'bg-danger';
            } else if (event.type === 'sabc_tournament') {
                eventTypeIcon = '<i class="bi bi-trophy me-2"></i>';
                eventTypeName = 'SABC Tournament';
                eventTypeClass = 'bg-primary';
            } else if (event.type === 'other_tournament') {
                eventTypeIcon = '<i class="bi bi-calendar-event me-2"></i>';
                eventTypeName = 'Other Tournament';
                eventTypeClass = 'bg-warning text-dark';
            } else if (event.type === 'club_event') {
                eventTypeIcon = '<i class="bi bi-people me-2"></i>';
                eventTypeName = 'Club Event';
                eventTypeClass = 'bg-success';
            } else if (event.type === 'generic_event') {
                eventTypeIcon = '<i class="bi bi-calendar me-2"></i>';
                eventTypeName = 'Event';
                eventTypeClass = 'bg-secondary';
            }

            modalContent += '<div class="mb-3">';
            modalContent += '<div class="d-flex align-items-center mb-2">';
            modalContent += '<span class="badge ' + eventTypeClass + ' me-2">' + eventTypeIcon + eventTypeName + '</span>';
            modalContent += '</div>';
            modalContent += '<h6 class="mb-2">' + escapeHtml(event.title || '') + '</h6>';
            if (event.description) {
                modalContent += '<p class="text-secondary mb-0">' + escapeHtml(event.description) + '</p>';
            }

            // Add tournament details if available (for sabc_tournament and other_tournament)
            // For SABC tournaments with active polls, only show lake/ramp (times are in the poll)
            // For other tournaments, show all details including times
            if (event.type === 'sabc_tournament' || event.type === 'other_tournament') {
                const showTimes = event.type === 'other_tournament' || !event.poll_id;
                if (event.lake_name || (showTimes && (event.start_time || event.end_time))) {
                    modalContent += '<div class="mt-2 small text-muted">';
                    if (event.lake_name) {
                        modalContent += '<div><i class="bi bi-geo-alt me-1" aria-hidden="true"></i><strong>Lake:</strong> ' + escapeHtml(event.lake_name);
                        if (event.ramp_name) {
                            modalContent += ' - ' + escapeHtml(event.ramp_name);
                        }
                        modalContent += '</div>';
                    }
                    if (showTimes && event.start_time) {
                        modalContent += '<div><i class="bi bi-clock me-1" aria-hidden="true"></i><strong>Start:</strong> ' + escapeHtml(event.start_time) + '</div>';
                    }
                    if (showTimes && event.end_time) {
                        modalContent += '<div><i class="bi bi-clock-fill me-1" aria-hidden="true"></i><strong>Weigh-in:</strong> ' + escapeHtml(event.end_time) + '</div>';
                    }
                    modalContent += '</div>';
                }
            }

            // Add poll and tournament links if available
            if (event.poll_id) {
                if (event.poll_status === 'active') {
                    modalContent += '<div class="mt-2">';
                    modalContent += '<a href="' + event.poll_link + '" class="btn btn-primary btn-sm me-2">';
                    modalContent += '<i class="bi bi-hand-thumbs-up me-1"></i>Vote in Poll</a>';
                    modalContent += '</div>';
                } else if (event.poll_status === 'closed' || event.poll_status === 'results') {
                    modalContent += '<div class="mt-2">';
                    modalContent += '<a href="' + event.poll_link + '" class="btn btn-secondary btn-sm me-2">';
                    modalContent += '<i class="bi bi-bar-chart me-1"></i>View Poll Results</a>';
                    modalContent += '</div>';
                }
            }

            if (event.tournament_link) {
                modalContent += '<div class="mt-2">';
                modalContent += '<a href="' + event.tournament_link + '" class="btn btn-success btn-sm">';
                modalContent += '<i class="bi bi-trophy me-1"></i>View Tournament Results</a>';
                modalContent += '</div>';
            }

            modalContent += '</div>';

            if (index < events.length - 1) {
                modalContent += '<hr>';
            }
        });

        // Set modal body
        document.getElementById('eventModalBody').innerHTML = modalContent;

        // Show modal
        showModal('eventModal');
    }
}
