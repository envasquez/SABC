/**
 * SABC Poll Management JavaScript
 * Shared functions for creating and editing polls
 */

/**
 * Format a date for datetime-local input
 * @param {Date|string} date - The date to format
 * @returns {string} Formatted date string (YYYY-MM-DDTHH:MM)
 */
function formatDateTimeLocal(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Add a new poll option to the container
 * @param {string} containerId - ID of the poll options container (default: 'poll-options-container')
 * @param {boolean} includeHiddenId - Whether to include a hidden option_id field (for edit mode)
 */
function addOption(containerId = 'poll-options-container', includeHiddenId = false) {
    const container = document.getElementById(containerId);
    const optionCount = container.children.length + 1;

    const optionRow = document.createElement('div');
    optionRow.className = 'poll-option-row mb-2';

    const hiddenField = includeHiddenId
        ? '<input type="hidden" name="option_ids[]" value="">'
        : '';

    optionRow.innerHTML = `
        <div class="input-group">
            <input type="text" class="form-control" name="poll_options[]" placeholder="Option ${optionCount}" required>
            ${hiddenField}
            <button class="btn btn-outline-danger" type="button" onclick="removeOption(this)">
                <i class="bi bi-x"></i>
            </button>
        </div>
    `;

    container.appendChild(optionRow);
    updateRemoveButtons(containerId);
}

/**
 * Remove a poll option
 * @param {HTMLElement} button - The remove button that was clicked
 * @param {boolean} checkVotes - Whether to confirm if option has votes
 */
function removeOption(button, checkVotes = true) {
    const row = button.closest('.poll-option-row');

    // Check if this option has votes (only in edit mode)
    if (checkVotes) {
        const votesBadge = row.querySelector('.input-group-text');
        if (votesBadge) {
            if (!confirm('This option has votes. Are you sure you want to remove it? All votes for this option will be deleted.')) {
                return;
            }
        }
    }

    row.remove();

    const container = button.closest('.poll-option-row').parentElement || document.getElementById('poll-options-container');
    if (container) {
        updateRemoveButtons(container.id);
        updatePlaceholders(container.id);
    }
}

/**
 * Update remove button states (disable if only 2 options remain)
 * @param {string} containerId - ID of the poll options container
 */
function updateRemoveButtons(containerId = 'poll-options-container') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const removeButtons = container.querySelectorAll('button[onclick*="removeOption"]');

    // Disable remove buttons if only 2 options remain
    removeButtons.forEach(button => {
        button.disabled = container.children.length <= 2;
    });
}

/**
 * Update option placeholders based on current index
 * @param {string} containerId - ID of the poll options container
 */
function updatePlaceholders(containerId = 'poll-options-container') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const inputs = container.querySelectorAll('input[name="poll_options[]"]');

    inputs.forEach((input, index) => {
        if (!input.value) {
            input.placeholder = `Option ${index + 1}`;
        }
    });
}

/**
 * Set intelligent poll timing defaults based on event date
 * @param {string|Date} eventDate - The event date
 * @param {string} startsAtId - ID of the starts_at input
 * @param {string} closesAtId - ID of the closes_at input
 */
function setOptimalPollTiming(eventDate, startsAtId, closesAtId) {
    const event = new Date(eventDate);
    const today = new Date();

    // Calculate optimal poll timing
    const daysBetween = Math.ceil((event - today) / (1000 * 60 * 60 * 24));

    let pollStart, pollClose;

    if (daysBetween > 14) {
        // For events more than 2 weeks out, start poll 10 days before event
        pollStart = new Date(event);
        pollStart.setDate(pollStart.getDate() - 10);
        pollClose = new Date(event);
        pollClose.setDate(pollClose.getDate() - 7);
    } else if (daysBetween > 7) {
        // For events 1-2 weeks out, start poll 7 days before event
        pollStart = new Date(event);
        pollStart.setDate(pollStart.getDate() - 7);
        pollClose = new Date(event);
        pollClose.setDate(pollClose.getDate() - 5);
    } else {
        // For events less than a week out, start poll today
        pollStart = new Date(today);
        pollStart.setDate(pollStart.getDate() + 1); // Tomorrow
        pollClose = new Date(event);
        pollClose.setDate(pollClose.getDate() - 2); // 2 days before event
    }

    // Set optimal times (poll starts at 6am for visibility, closes at 6pm for decisions)
    pollStart.setHours(6, 0, 0, 0);
    pollClose.setHours(18, 0, 0, 0);

    // Set the input values
    const startsAtInput = document.getElementById(startsAtId);
    const closesAtInput = document.getElementById(closesAtId);

    if (startsAtInput) startsAtInput.value = formatDateTimeLocal(pollStart);
    if (closesAtInput) closesAtInput.value = formatDateTimeLocal(pollClose);
}
