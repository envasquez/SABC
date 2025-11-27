/**
 * SABC Admin Events Management - Core Module
 * JavaScript for /admin/events page - event editing, deletion, and initialization
 *
 * This module depends on:
 * - admin-events-lakes.js (lake/ramp loading)
 * - admin-events-forms.js (form field management)
 * - admin-events-filters.js (event filtering)
 * - utils.js (LakeRampSelector, formatDateTimeLocal, deleteRequest, showToast)
 */

/**
 * Edit an event - loads event data and shows edit modal
 * @param {number} id - Event ID
 * @param {string} date - Event date
 * @param {string} eventType - Event type
 * @param {string} name - Event name
 * @param {string} description - Event description
 * @param {boolean} hasPoll - Whether event has a poll
 */
function editEvent(id, date, eventType, name, description, hasPoll) {
    // Ensure lakes are loaded before proceeding
    const ensureLakesLoadedAndEdit = () => {
        // Fetch complete event data
        fetch(`/admin/events/${id}/info`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showToast('Error loading event data: ' + data.error, 'error');
                    return;
                }

                // Set basic event fields
                document.getElementById('edit_event_id').value = id;
                document.getElementById('edit_date').value = data.date || date;
                document.getElementById('edit_event_type').value = data.event_type || eventType;
                document.getElementById('edit_name').value = data.name || name || '';
                document.getElementById('edit_description').value = data.description || description || '';

                // Toggle visibility of event type-specific fields FIRST
                toggleEditEventFields();

                // Handle tournament fields (both SABC and Other tournaments)
                if (data.event_type === 'sabc_tournament' || data.event_type === 'other_tournament') {
                    // Set tournament-specific fields (times are optional for other_tournament)
                    const startTime = document.getElementById('edit_start_time');
                    if (startTime) {
                        startTime.value = data.start_time || '';
                    }

                    const weighInTime = document.getElementById('edit_weigh_in_time');
                    if (weighInTime) {
                        weighInTime.value = data.weigh_in_time || '';
                    }

                    // SABC-specific fields
                    if (data.event_type === 'sabc_tournament') {
                        const entryFee = document.getElementById('edit_entry_fee');
                        if (entryFee) {
                            entryFee.value = data.entry_fee !== undefined ? data.entry_fee : '';
                        }

                        const fishLimit = document.getElementById('edit_fish_limit');
                        if (fishLimit) {
                            fishLimit.value = data.fish_limit !== undefined ? data.fish_limit : '';
                        }

                        const aoyPoints = document.getElementById('edit_aoy_points');
                        if (aoyPoints) {
                            aoyPoints.value = data.aoy_points ? 'true' : 'false';
                        }
                    }

                    // Set lake - make sure the option exists in the dropdown
                    const lakeSelect = document.getElementById('edit_lake_name');
                    if (lakeSelect && data.lake_name) {
                        // Check if the option exists
                        const lakeOption = Array.from(lakeSelect.options).find(opt => opt.value === data.lake_name);
                        if (lakeOption) {
                            lakeSelect.value = data.lake_name;
                            // Then load ramps for this lake and await completion
                            loadRamps(data.lake_name, 'edit_ramp_name').then(() => {
                                const rampSelect = document.getElementById('edit_ramp_name');
                                if (rampSelect && data.ramp_name) {
                                    rampSelect.value = data.ramp_name;
                                }
                            }).catch(error => {
                                console.error('Error setting ramp selection:', error);
                            });
                        }
                    }
                }

                // Handle holiday fields
                if (data.event_type === 'holiday' && data.holiday_name) {
                    const holidayName = document.getElementById('edit_holiday_name');
                    if (holidayName) {
                        holidayName.value = data.holiday_name;
                    }
                }

                // Setup poll fields
                setupPollFields(data.event_type, hasPoll, data.poll_closes_at);

                // Show the modal
                const modal = new bootstrap.Modal(document.getElementById('editEventModal'));
                modal.show();
            })
            .catch(error => {
                console.error('Error loading event data:', error);
                showToast('Error loading event data. Please try again.', 'error');
            });
    };

    // Check if lakes are already loaded
    const currentLakesData = getLakesData();
    if (currentLakesData.length === 0) {
        fetch('/api/lakes')
            .then(response => response.json())
            .then(lakes => {
                setLakesData(lakes);
                ensureLakesLoadedAndEdit();
            })
            .catch(error => {
                console.error('Error loading lakes:', error);
                // Still try to edit without lakes
                ensureLakesLoadedAndEdit();
            });
    } else {
        ensureLakesLoadedAndEdit();
    }
}

/**
 * Setup poll fields in edit modal
 * @param {string} eventType - Event type
 * @param {boolean} hasPoll - Whether event has a poll
 * @param {string} pollClosesAt - Poll close datetime
 */
function setupPollFields(eventType, hasPoll, pollClosesAt) {
    var pollClosesContainer = document.getElementById('edit_poll_closes_container');
    var pollClosesInput = document.getElementById('edit_poll_closes_date');

    if (eventType === 'sabc_tournament' && hasPoll) {
        pollClosesContainer.style.display = 'block';
        if (pollClosesAt) {
            // Use shared formatDateTimeLocal from utils.js
            pollClosesInput.value = formatDateTimeLocal(pollClosesAt);
        }
    } else {
        pollClosesContainer.style.display = 'none';
    }
}


/**
 * Unified delete event handler - works for both current and past events
 * @param {number} id - Event ID to delete
 * @param {boolean} hasDependencies - Whether event has dependencies (polls, tournaments)
 * @param {string} eventName - Event name for display
 * @param {string} context - 'current' or 'past' to determine which modal to use
 */
function showDeleteEventModal(id, hasDependencies, eventName = 'Event', context = 'current') {
    const modalId = context === 'current' ? 'deleteEventModal' : 'deletePastEventModal';
    const prefix = context === 'current' ? 'delete-current' : 'delete';

    // Set the event name in the modal
    document.getElementById(`${prefix}-event-name`).textContent = eventName;
    document.getElementById(`${prefix}-event-id`).value = id;

    // Show/hide dependencies warning
    const warningElement = document.getElementById(`${prefix}-dependencies-warning`);
    warningElement.style.display = hasDependencies ? 'block' : 'none';

    // Clear the confirmation input
    document.getElementById(`${prefix}-confirmation`).value = '';

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

/**
 * Confirm and execute event deletion
 * @param {string} context - 'current' or 'past' to determine which modal elements to use
 */
async function confirmDeleteEvent(context = 'current') {
    const modalId = context === 'current' ? 'deleteEventModal' : 'deletePastEventModal';
    const prefix = context === 'current' ? 'delete-current' : 'delete';

    const confirmText = document.getElementById(`${prefix}-confirmation`).value;
    const eventId = document.getElementById(`${prefix}-event-id`).value;

    if (confirmText.trim() !== 'DELETE') {
        showToast('Please type DELETE to confirm', 'warning');
        return;
    }

    // Close the modal
    bootstrap.Modal.getInstance(document.getElementById(modalId)).hide();

    try {
        const response = await deleteRequest(`/admin/events/${eventId}`);

        if (response.ok) {
            showToast('Event deleted successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            const data = await response.json().catch(() => ({}));
            const errorMsg = data.error || 'Failed to delete event';

            if (response.status === 400) {
                showToast(`Cannot delete event: ${errorMsg}`, 'error');
            } else {
                showToast(`Error deleting event: ${errorMsg}`, 'error');
            }
        }
    } catch (error) {
        showToast(`Network error: ${error.message}`, 'error');
    }
}

// Wrapper functions for backward compatibility with existing HTML onclick handlers
function deleteEvent(id, hasDependencies, eventName = 'Event') {
    showDeleteEventModal(id, hasDependencies, eventName, 'current');
}

function confirmDeleteCurrentEvent() {
    confirmDeleteEvent('current');
}

function deletePastEvent(id, name, hasDependencies) {
    showDeleteEventModal(id, hasDependencies, name, 'past');
}

function confirmDeletePastEvent() {
    confirmDeleteEvent('past');
}

/**
 * Setup all event listeners when DOM is ready
 */
function setupEventListeners() {
    // Load lakes on page load (this will also populate other tournament dropdown)
    loadLakes();

    // Event type change handlers
    const eventTypeSelect = document.getElementById('event_type');
    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', toggleEventFields);
    }

    const editEventTypeSelect = document.getElementById('edit_event_type');
    if (editEventTypeSelect) {
        editEventTypeSelect.addEventListener('change', toggleEditEventFields);
    }

    // Lake selection handlers
    const lakeSelect = document.getElementById('lake_name');
    if (lakeSelect) {
        lakeSelect.addEventListener('change', function() {
            loadRamps(this.value, 'ramp_name');
        });
    }

    const editLakeSelect = document.getElementById('edit_lake_name');
    if (editLakeSelect) {
        editLakeSelect.addEventListener('change', function() {
            loadRamps(this.value, 'edit_ramp_name');
        });
    }

    const otherLakeSelect = document.getElementById('other_lake_name');
    if (otherLakeSelect) {
        otherLakeSelect.addEventListener('change', function() {
            loadRamps(this.value, 'other_ramp_name');
        });
    }

    // Initialize with default state
    toggleEventFields();

    // Auto-populate tournament name based on date
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            const nameInput = document.getElementById('name');
            const eventType = document.getElementById('event_type').value;

            if (eventType === 'sabc_tournament' && this.value && !nameInput.value) {
                const date = new Date(this.value);
                const month = date.toLocaleString('default', { month: 'long' });
                const year = date.getFullYear();
                nameInput.value = `${month} ${year} Tournament`;
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', setupEventListeners);
