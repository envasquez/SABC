/**
 * SABC Admin Events Management
 * JavaScript for /admin/events page - event creation, editing, filtering
 */

// Load lakes when page loads
let lakesData = [];
function loadLakes() {
    fetch('/api/lakes')
        .then(response => response.json())
        .then(lakes => {
            lakesData = lakes;
            // Populate create form lake select
            const createLakeSelect = document.getElementById('lake_name');
            if (createLakeSelect) {
                createLakeSelect.innerHTML = '<option value="">-- Select Lake --</option>';
                lakes.forEach(lake => {
                    const option = document.createElement('option');
                    option.value = lake.name;
                    option.textContent = lake.name;
                    option.dataset.lakeKey = lake.key;
                    createLakeSelect.appendChild(option);
                });
            }

            // Populate edit form lake select
            const editLakeSelect = document.getElementById('edit_lake_name');
            if (editLakeSelect) {
                editLakeSelect.innerHTML = '<option value="">-- Select Lake --</option>';
                lakes.forEach(lake => {
                    const option = document.createElement('option');
                    option.value = lake.name;
                    option.textContent = lake.name;
                    option.dataset.lakeKey = lake.key;
                    editLakeSelect.appendChild(option);
                });
            }

            // Populate other tournament lake select
            loadLakesForOtherTournament();
        });
}

/**
 * Load boat ramps for a selected lake using LakeRampSelector component
 * Fetches ramps from API and populates the specified select element
 *
 * @param {string} lakeName - Name of the lake to load ramps for
 * @param {string} rampSelectId - ID of the select element to populate (default: 'edit_ramp_name')
 * @returns {Promise<void>} Promise that resolves when ramps are loaded
 */
async function loadRamps(lakeName, rampSelectId = 'edit_ramp_name') {
    // Create a temporary lake select ID (not used but required by component)
    const tempLakeId = `temp_lake_for_${rampSelectId}`;

    const selector = new LakeRampSelector({
        lakeSelectId: tempLakeId,
        rampSelectId: rampSelectId,
        lakesData: lakesData,
        useApi: true
    });

    await selector.loadRampsForLake(lakeName);
}

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

                // Handle SABC tournament fields
                if (data.event_type === 'sabc_tournament') {
                    // Set tournament-specific fields
                    const startTime = document.getElementById('edit_start_time');
                    if (startTime) {
                        startTime.value = data.start_time || '';
                    }

                    const weighInTime = document.getElementById('edit_weigh_in_time');
                    if (weighInTime) {
                        weighInTime.value = data.weigh_in_time || '';
                    }

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
    if (lakesData.length === 0) {
        fetch('/api/lakes')
            .then(response => response.json())
            .then(lakes => {
                lakesData = lakes;
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

function setupPollFields(eventType, hasPoll, pollClosesAt) {

    var pollClosesContainer = document.getElementById('edit_poll_closes_container');
    var pollClosesInput = document.getElementById('edit_poll_closes_date');

    if (eventType === 'sabc_tournament' && hasPoll) {
        pollClosesContainer.style.display = 'block';
        if (pollClosesAt) {
            // Format the datetime for the input
            const date = new Date(pollClosesAt);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            pollClosesInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
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

// Configuration-driven event form management
// Base configurations for reuse
const BASE_TOURNAMENT_CONFIG = {
    clearFields: ['start_time', 'weigh_in_time'],
    defaults: { start_time: '06:00', weigh_in_time: '15:00' },
    requiredFields: []
};

const EMPTY_CONFIG = {
    clearFields: [],
    defaults: {},
    requiredFields: []
};

const EVENT_FORM_CONFIG = {
    sabc_tournament: {
        ...BASE_TOURNAMENT_CONFIG,
        visibleSections: ['sabc-tournament-fields'],
        editSections: ['edit-tournament-fields', 'edit-sabc-fields'],
        descriptionField: 'description'
    },
    holiday: {
        ...EMPTY_CONFIG,
        visibleSections: ['holiday-fields'],
        editSections: ['edit-holiday-fields'],
        descriptionField: null
    },
    other_tournament: {
        ...EMPTY_CONFIG,
        visibleSections: ['other-tournament-fields', 'other-tournament-description'],
        editSections: ['edit-tournament-fields'],
        descriptionField: 'other_description'
    }
};

/**
 * Utility: Hide all specified sections and disable their inputs
 */
function hideAllSections(sectionIds) {
    sectionIds.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.style.display = 'none';
            // Disable all inputs in hidden sections so they don't submit
            section.querySelectorAll('input, select, textarea').forEach(input => {
                input.disabled = true;
            });
        }
    });
}

/**
 * Utility: Show specified sections and enable their inputs
 */
function showSections(sectionIds, displayType = 'flex') {
    sectionIds.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.style.display = displayType;
            // Enable all inputs in visible sections
            section.querySelectorAll('input, select, textarea').forEach(input => {
                // Don't enable ramp selects - they're controlled by lake selection
                if (!input.id.includes('ramp_name')) {
                    input.disabled = false;
                }
            });
        }
    });
}

/**
 * Utility: Clear specified form field values
 */
function clearFieldValues(fieldIds) {
    fieldIds.forEach(id => {
        const field = document.getElementById(id);
        if (field) field.value = '';
    });
}

/**
 * Utility: Set default values for specified fields
 */
function setFieldDefaults(fieldValueMap) {
    Object.entries(fieldValueMap).forEach(([fieldId, value]) => {
        const field = document.getElementById(fieldId);
        if (field) field.value = value;
    });
}

/**
 * Utility: Clear all 'required' attributes from form fields
 */
function clearAllRequirements() {
    ['start_time', 'weigh_in_time', 'lake_name', 'ramp_name', 'other_description'].forEach(id => {
        const field = document.getElementById(id);
        if (field) field.removeAttribute('required');
    });
}

/**
 * Utility: Set 'required' attribute on specified fields
 */
function setFieldRequirements(requiredIds) {
    requiredIds.forEach(id => {
        const field = document.getElementById(id);
        if (field) field.setAttribute('required', 'required');
    });
}

/**
 * Manage description fields based on event type
 */
function manageDescriptionFields(activeFieldId) {
    const descriptionField = document.getElementById('description');
    const otherDescriptionField = document.getElementById('other_description');

    if (activeFieldId === 'other_description') {
        // Hide general description, show other_description
        if (descriptionField) {
            descriptionField.closest('.col-md-3').style.display = 'none';
            descriptionField.removeAttribute('required');
        }
        if (otherDescriptionField) {
            otherDescriptionField.closest('.col-md-12').style.display = 'block';
            otherDescriptionField.setAttribute('required', 'required');
        }
    } else if (activeFieldId === 'description') {
        // Show general description, hide other_description
        if (descriptionField) {
            descriptionField.closest('.col-md-3').style.display = 'block';
        }
        if (otherDescriptionField) {
            otherDescriptionField.closest('.col-md-12').style.display = 'none';
            otherDescriptionField.removeAttribute('required');
        }
    } else {
        // No description field active
        if (descriptionField) {
            descriptionField.closest('.col-md-3').style.display = 'block';
        }
        if (otherDescriptionField) {
            otherDescriptionField.closest('.col-md-12').style.display = 'none';
            otherDescriptionField.removeAttribute('required');
        }
    }
}

/**
 * Get selected event type (create or edit mode)
 */
function getSelectedEventType(isEdit = false) {
    const selectId = isEdit ? 'edit_event_type' : 'event_type';
    return document.getElementById(selectId)?.value;
}

/**
 * Toggle visibility of event-type-specific fields (create form)
 */
function toggleEventFields() {
    const eventType = getSelectedEventType(false);
    const config = EVENT_FORM_CONFIG[eventType];

    if (!config) return;

    // Hide all possible sections first
    const allSections = ['sabc-tournament-fields', 'other-tournament-fields',
                        'other-tournament-description', 'other-fields', 'sabc-fields', 'holiday-fields'];
    hideAllSections(allSections);

    // Show relevant sections for this event type
    showSections(config.visibleSections);

    // Clear requirements and set new ones
    clearAllRequirements();
    setFieldRequirements(config.requiredFields);

    // Handle description field visibility
    manageDescriptionFields(config.descriptionField);

    // Set default values
    setFieldDefaults(config.defaults);

    // Update name field requirement indicator
    const nameRequired = document.getElementById('name-required');
    if (nameRequired) {
        nameRequired.style.display = eventType === 'holiday' ? 'none' : 'inline';
    }
}

/**
 * Toggle visibility of event-type-specific fields (edit form)
 */
function toggleEditEventFields() {
    const eventType = getSelectedEventType(true);
    const config = EVENT_FORM_CONFIG[eventType];

    if (!config) return;

    // Hide all edit sections first
    const allEditSections = ['edit-tournament-fields', 'edit-sabc-fields', 'edit-holiday-fields'];
    hideAllSections(allEditSections);

    // Show relevant edit sections using 'block' display
    showSections(config.editSections, 'block');
}

/**
 * Populate other tournament lake dropdown from cached lakesData
 */
function loadLakesForOtherTournament() {
    const lakeSelect = document.getElementById('other_lake_name');
    if (lakeSelect && lakesData.length > 0) {
        lakeSelect.innerHTML = '<option value="">-- Select Lake (Optional) --</option>';
        lakesData.forEach(lake => {
            const option = document.createElement('option');
            option.value = lake.name;
            option.textContent = lake.name;
            option.dataset.lakeKey = lake.key;
            lakeSelect.appendChild(option);
        });
    }
}

/**
 * Filter events in a specific tab
 */
function filterEvents(tabType) {
    const searchInput = document.getElementById(`${tabType}-search`).value.toLowerCase();
    const yearFilter = document.getElementById(`${tabType}-year-filter`)?.value;
    const statusFilter = document.getElementById(`${tabType}-status-filter`)?.value;
    const lakeFilter = document.getElementById(`${tabType}-lake-filter`)?.value.toLowerCase();
    const typeFilter = document.getElementById(`${tabType}-type-filter`)?.value;
    const resultsFilter = document.getElementById(`${tabType}-results-filter`)?.value;

    // Determine the correct table selector based on tab type
    let tableSelector;
    if (tabType === 'past') {
        tableSelector = '#past-events-tab table tbody tr';
    } else if (tabType === 'past-tournaments') {
        tableSelector = '#past-tournaments-events table tbody tr';
    } else {
        tableSelector = `#${tabType}-events table tbody tr`;
    }

    const rows = document.querySelectorAll(tableSelector);
    let visibleCount = 0;

    rows.forEach(row => {
        // Skip rows with no data cells (e.g., empty state messages)
        if (row.cells.length < 3) {
            return;
        }

        let visible = true;

        // Search filter
        if (searchInput && !row.textContent.toLowerCase().includes(searchInput)) {
            visible = false;
        }

        // Year filter
        if (yearFilter && row.dataset.year !== yearFilter) {
            visible = false;
        }

        // Status filter (for SABC tournaments)
        if (statusFilter) {
            if (statusFilter === 'has-poll' && !row.textContent.includes('🗳️')) {
                visible = false;
            }
            if (statusFilter === 'no-poll' && row.textContent.includes('🗳️')) {
                visible = false;
            }
            if (statusFilter === 'complete' && !row.textContent.includes('✅')) {
                visible = false;
            }
            if (statusFilter === 'incomplete' && row.textContent.includes('✅')) {
                visible = false;
            }
        }

        // Lake filter
        if (lakeFilter && row.dataset.lake && !row.dataset.lake.includes(lakeFilter)) {
            visible = false;
        }

        // Type filter
        if (typeFilter && row.dataset.eventType !== typeFilter) {
            visible = false;
        }

        // Results filter
        if (resultsFilter) {
            const hasResults = row.dataset.hasResults === 'yes';
            if (resultsFilter === 'has-results' && !hasResults) {
                visible = false;
            }
            if (resultsFilter === 'no-results' && hasResults) {
                visible = false;
            }
        }

        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
    });

    // Update empty state
    updateEmptyState(tabType, visibleCount);
}

function clearFilters(tabType) {
    // Clear all filter inputs for this tab
    document.getElementById(`${tabType}-search`).value = '';

    const yearFilter = document.getElementById(`${tabType}-year-filter`);
    if (yearFilter) yearFilter.value = '';

    const statusFilter = document.getElementById(`${tabType}-status-filter`);
    if (statusFilter) statusFilter.value = '';

    const lakeFilter = document.getElementById(`${tabType}-lake-filter`);
    if (lakeFilter) lakeFilter.value = '';

    const typeFilter = document.getElementById(`${tabType}-type-filter`);
    if (typeFilter) typeFilter.value = '';

    const resultsFilter = document.getElementById(`${tabType}-results-filter`);
    if (resultsFilter) resultsFilter.value = '';

    // Show all rows
    let tableSelector;
    if (tabType === 'past') {
        tableSelector = '#past-events-tab table tbody tr';
    } else if (tabType === 'past-tournaments') {
        tableSelector = '#past-tournaments-events table tbody tr';
    } else {
        tableSelector = `#${tabType}-events table tbody tr`;
    }

    const rows = document.querySelectorAll(tableSelector);
    let visibleCount = 0;

    rows.forEach(row => {
        if (row.cells.length > 2 && !row.textContent.includes('No events')) {
            row.style.display = '';
            visibleCount++;
        }
    });

    updateEmptyState(tabType, visibleCount);
}

function updateEmptyState(tabType, visibleCount) {
    // Update tab badges with filtered counts
    let badgeId;
    if (tabType === 'sabc') badgeId = 'sabc-count';
    else if (tabType === 'holidays') badgeId = 'holidays-count';
    else if (tabType === 'other') badgeId = 'other-count';
    else if (tabType === 'past-tournaments') badgeId = 'past-tournaments-count';
    else if (tabType === 'past') badgeId = 'past-count';

    const tabBadge = document.getElementById(badgeId);

    if (tabBadge && visibleCount !== undefined) {
        // Store original count if not already stored
        if (!tabBadge.dataset.originalCount) {
            tabBadge.dataset.originalCount = tabBadge.textContent;
        }

        // Show filtered count if different from original
        if (document.getElementById(`${tabType}-search`).value ||
            document.getElementById(`${tabType}-year-filter`)?.value ||
            document.getElementById(`${tabType}-status-filter`)?.value ||
            document.getElementById(`${tabType}-lake-filter`)?.value ||
            document.getElementById(`${tabType}-type-filter`)?.value ||
            document.getElementById(`${tabType}-results-filter`)?.value) {
            tabBadge.textContent = visibleCount;
            tabBadge.classList.add('bg-warning');
            tabBadge.classList.remove('bg-primary', 'bg-info', 'bg-secondary');
        } else {
            tabBadge.textContent = tabBadge.dataset.originalCount;
            tabBadge.classList.remove('bg-warning');
            // Restore original badge color based on tab
            if (tabType === 'sabc') tabBadge.classList.add('bg-primary');
            else if (tabType === 'holidays') tabBadge.classList.add('bg-info');
            else if (tabType === 'other') tabBadge.classList.add('bg-warning');
            else tabBadge.classList.add('bg-secondary');
        }
    }
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
