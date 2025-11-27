/**
 * Admin Events - Form Configuration Module
 * Handles event type-specific form field visibility and validation
 */

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
