/**
 * SABC Poll Voting Handler
 * Centralized voting logic for all poll types
 */

(function() {
    'use strict';

/**
 * PollVotingHandler - Manages poll voting interactions
 * Eliminates per-poll generated JavaScript by using data attributes and generic handlers
 *
 * @class
 *
 * @example
 * // Initialize with lakes data
 * const votingHandler = new PollVotingHandler(lakesData);
 * votingHandler.initialize();
 */
class PollVotingHandler {
    /**
     * Create a PollVotingHandler instance
     * @param {Array|Object} lakesData - Lakes and ramps data structure
     */
    constructor(lakesData) {
        this.lakesData = lakesData;
        this.pendingForm = null;  // Store form awaiting confirmation
        this.confirmModal = null;  // Bootstrap modal instance
    }

    /**
     * Initialize all poll voting handlers
     * Sets up event listeners for all polls on the page
     */
    initialize() {
        // Set up lake/ramp cascading dropdowns
        this.setupLakeRampHandlers();

        // Set up form validation
        this.setupFormValidation();

        // Set up confirmation modal
        this.setupConfirmationModal();
    }

    /**
     * Set up lake selection handlers that populate ramp dropdowns
     * @private
     */
    setupLakeRampHandlers() {
        // Find all lake selects with data-poll-id attribute
        const lakeSelects = document.querySelectorAll('select[data-poll-lake]');

        lakeSelects.forEach(lakeSelect => {
            lakeSelect.addEventListener('change', (e) => {
                this.handleLakeChange(e.target);
            });
        });
    }

    /**
     * Handle lake selection change - populate corresponding ramp dropdown
     * @param {HTMLSelectElement} lakeSelect - The lake select element that changed
     * @private
     */
    handleLakeChange(lakeSelect) {
        const pollId = lakeSelect.dataset.pollId;
        const context = lakeSelect.dataset.context; // 'admin_own', 'admin_proxy', 'nonadmin'

        // Find the corresponding ramp select
        const rampSelectId = this.getRampSelectId(pollId, context);
        const rampSelect = document.getElementById(rampSelectId);

        if (!rampSelect) {
            console.error('Ramp select not found: ' + rampSelectId);
            return;
        }

        // Clear and disable ramp select
        rampSelect.innerHTML = '<option value="">Select a ramp...</option>';
        rampSelect.disabled = true;

        const lakeId = parseInt(lakeSelect.value);
        if (!lakeId) return;

        // Find selected lake in data
        const selectedLake = this.findLake(lakeId);
        if (!selectedLake || !selectedLake.ramps) {
            console.error('Lake not found or has no ramps: ' + lakeId);
            return;
        }

        // Populate ramps
        selectedLake.ramps.forEach(ramp => {
            const option = document.createElement('option');
            option.value = ramp.id;
            option.textContent = ramp.name;
            rampSelect.appendChild(option);
        });

        if (selectedLake.ramps.length > 0) {
            rampSelect.disabled = false;
        }
    }

    /**
     * Find lake in lakes data by ID
     * @param {number} lakeId - Lake ID to find
     * @returns {Object|null} Lake object or null
     * @private
     */
    findLake(lakeId) {
        if (Array.isArray(this.lakesData)) {
            return this.lakesData.find(lake => lake.id === lakeId);
        }
        // Handle object format: {1: {name: '...', ramps: [...]}, ...}
        return this.lakesData[lakeId] || null;
    }

    /**
     * Get ramp select ID based on poll ID and context
     * @param {string|number} pollId - Poll ID
     * @param {string} context - Context: 'admin_own', 'admin_proxy', 'nonadmin'
     * @returns {string} Ramp select element ID
     * @private
     */
    getRampSelectId(pollId, context) {
        const prefixes = {
            'admin_own': 'ramp_select_admin_own_',
            'admin_proxy': 'admin_ramp_select_',
            'nonadmin': 'ramp_select_nonadmin_'
        };
        return prefixes[context] + pollId;
    }

    /**
     * Set up form validation handlers
     * @private
     */
    setupFormValidation() {
        // Find all poll voting forms
        const voteForms = document.querySelectorAll('form[data-poll-vote]');

        voteForms.forEach(form => {
            form.addEventListener('submit', (e) => {
                // Always prevent default - we'll submit via confirmation modal
                e.preventDefault();

                if (!this.validateVoteForm(form)) {
                    return false;
                }

                // Show confirmation modal instead of submitting
                this.showConfirmation(form);
            });
        });
    }

    /**
     * Set up confirmation modal event handlers
     * @private
     */
    setupConfirmationModal() {
        const modalElement = document.getElementById('voteConfirmModal');
        if (!modalElement) return;

        // Initialize Bootstrap modal
        this.confirmModal = new bootstrap.Modal(modalElement);

        // Handle confirm button click
        const confirmBtn = document.getElementById('confirmVoteBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (this.pendingForm) {
                    // Hide modal first
                    this.confirmModal.hide();
                    // Submit the form programmatically (bypassing the event listener)
                    this.submitPendingForm();
                }
            });
        }

        // Clear pending form when modal is closed
        modalElement.addEventListener('hidden.bs.modal', () => {
            // Only clear if we didn't submit
            if (this.pendingForm && !this.pendingForm.dataset.submitting) {
                this.pendingForm = null;
            }
        });
    }

    /**
     * Submit the pending form directly
     * @private
     */
    submitPendingForm() {
        if (!this.pendingForm) return;

        // Mark as submitting to prevent clearing
        this.pendingForm.dataset.submitting = 'true';

        // Create a hidden submit button and click it to submit the form
        // This bypasses our event listener which calls preventDefault
        const submitBtn = document.createElement('button');
        submitBtn.type = 'submit';
        submitBtn.style.display = 'none';
        submitBtn.name = '_confirm_submit';
        this.pendingForm.appendChild(submitBtn);

        // Remove our submit handler temporarily
        const form = this.pendingForm;
        this.pendingForm = null;

        // Use HTMLFormElement.submit() to bypass event listeners
        form.submit();
    }

    /**
     * Show vote confirmation modal with summary
     * @param {HTMLFormElement} form - The form to confirm
     * @private
     */
    showConfirmation(form) {
        if (!this.confirmModal) {
            // No modal available, just submit
            form.submit();
            return;
        }

        this.pendingForm = form;
        const pollId = form.dataset.pollId;
        const pollType = form.dataset.pollType;
        const context = form.dataset.context;

        // Get poll title from the page
        const pollCard = form.closest('.card');
        const pollTitle = pollCard ? pollCard.querySelector('.card-title, h5')?.textContent?.trim() : 'Poll';

        // Set the poll title in the modal
        const titleElement = document.getElementById('voteConfirmPollTitle');
        if (titleElement) {
            titleElement.textContent = pollTitle;
        }

        // Generate summary based on poll type
        const summaryElement = document.getElementById('voteConfirmSummary');
        if (summaryElement) {
            summaryElement.innerHTML = this.generateVoteSummary(form, pollType, pollId, context);
        }

        // Show the modal
        this.confirmModal.show();
    }

    /**
     * Generate HTML summary of the vote
     * @param {HTMLFormElement} form - The form
     * @param {string} pollType - Type of poll
     * @param {string|number} pollId - Poll ID
     * @param {string} context - Context (admin_own, admin_proxy, nonadmin)
     * @returns {string} HTML summary
     * @private
     */
    generateVoteSummary(form, pollType, pollId, context) {
        if (pollType === 'tournament_location') {
            return this.generateTournamentSummary(pollId, context);
        } else {
            return this.generateSimpleSummary(form);
        }
    }

    /**
     * Generate summary for tournament location vote
     * @param {string|number} pollId - Poll ID
     * @param {string} context - Context
     * @returns {string} HTML summary
     * @private
     */
    generateTournamentSummary(pollId, context) {
        const ids = this.getElementIds(pollId, context);

        const lakeSelect = document.getElementById(ids.lake);
        const rampSelect = document.getElementById(ids.ramp);
        const startTimeSelect = document.getElementById(ids.startTime);
        const endTimeSelect = document.getElementById(ids.endTime);

        const lakeName = lakeSelect?.selectedOptions[0]?.text || 'Unknown';
        const rampName = rampSelect?.selectedOptions[0]?.text || 'Unknown';
        // Shared formatter from utils.js; fall back to 'Unknown' for empty values
        const startTime = startTimeSelect?.value ? formatTime12Hour(startTimeSelect.value) : 'Unknown';
        const endTime = endTimeSelect?.value ? formatTime12Hour(endTimeSelect.value) : 'Unknown';

        let summary = '<dl class="row mb-0">';
        summary += '<dt class="col-sm-4"><i class="bi bi-geo-alt me-1"></i>Lake</dt>';
        summary += '<dd class="col-sm-8 fw-bold">' + escapeHtml(lakeName) + '</dd>';
        summary += '<dt class="col-sm-4"><i class="bi bi-signpost me-1"></i>Ramp</dt>';
        summary += '<dd class="col-sm-8 fw-bold">' + escapeHtml(rampName) + '</dd>';
        summary += '<dt class="col-sm-4"><i class="bi bi-clock me-1"></i>Start Time</dt>';
        summary += '<dd class="col-sm-8 fw-bold">' + startTime + '</dd>';
        summary += '<dt class="col-sm-4"><i class="bi bi-clock-history me-1"></i>End Time</dt>';
        summary += '<dd class="col-sm-8 fw-bold">' + endTime + '</dd>';
        summary += '</dl>';

        // For proxy votes, show who we're voting for
        if (context === 'admin_proxy') {
            const memberSelect = document.getElementById(ids.member);
            const memberName = memberSelect?.selectedOptions[0]?.text || 'Unknown';
            summary += '<div class="mt-2 pt-2 border-top">';
            summary += '<small class="text-warning"><i class="bi bi-person-badge me-1"></i>Voting on behalf of: <strong>' + escapeHtml(memberName) + '</strong></small>';
            summary += '</div>';
        }

        return summary;
    }

    /**
     * Generate summary for simple poll vote
     * @param {HTMLFormElement} form - The form
     * @returns {string} HTML summary
     * @private
     */
    generateSimpleSummary(form) {
        const selectedOption = form.querySelector('input[name="option_id"]:checked');
        if (!selectedOption) {
            return '<p class="text-warning">No option selected</p>';
        }

        const label = form.querySelector('label[for="' + selectedOption.id + '"]');
        const optionText = label ? label.textContent.trim() : 'Unknown option';

        let summary = '<div class="d-flex align-items-center">';
        summary += '<i class="bi bi-check-circle-fill text-success me-2" style="font-size: 1.5rem;"></i>';
        summary += '<span class="fw-bold">' + escapeHtml(optionText) + '</span>';
        summary += '</div>';

        return summary;
    }

    /**
     * Validate a poll vote form
     * @param {HTMLFormElement} form - Form to validate
     * @returns {boolean} True if valid
     * @private
     */
    validateVoteForm(form) {
        const pollId = form.dataset.pollId;
        const pollType = form.dataset.pollType;
        const context = form.dataset.context;

        if (pollType === 'tournament_location') {
            return this.validateTournamentVote(pollId, context);
        } else {
            return this.validateSimpleVote(pollId, context);
        }
    }

    /**
     * Validate tournament location vote
     * @param {string|number} pollId - Poll ID
     * @param {string} context - Context: 'admin_own', 'admin_proxy', 'nonadmin'
     * @returns {boolean} True if valid
     * @private
     */
    validateTournamentVote(pollId, context) {
        // Get element IDs based on context
        const ids = this.getElementIds(pollId, context);

        // Get elements
        const lakeSelect = document.getElementById(ids.lake);
        const rampSelect = document.getElementById(ids.ramp);
        const startTimeSelect = document.getElementById(ids.startTime);
        const endTimeSelect = document.getElementById(ids.endTime);
        const voteDataInput = document.getElementById(ids.voteData);

        // For proxy votes, also check member selection
        if (context === 'admin_proxy') {
            const memberSelect = document.getElementById(ids.member);
            if (!memberSelect || !memberSelect.value) {
                showToast('Please select a member to vote for', 'warning');
                return false;
            }
        }

        // Validate lake
        if (!lakeSelect || !lakeSelect.value) {
            showToast('Please select a lake', 'warning');
            return false;
        }

        // Validate ramp
        if (!rampSelect || !rampSelect.value) {
            showToast('Please select a ramp', 'warning');
            return false;
        }

        // Validate start time
        if (!startTimeSelect || !startTimeSelect.value) {
            showToast('Please select a start time', 'warning');
            return false;
        }

        // Validate end time
        if (!endTimeSelect || !endTimeSelect.value) {
            showToast('Please select an end time', 'warning');
            return false;
        }

        // Validate time order
        if (startTimeSelect.value >= endTimeSelect.value) {
            showToast('Start time must be before end time', 'warning');
            return false;
        }

        // Validate reasonable tournament hours
        const startHour = parseInt(startTimeSelect.value.split(':')[0]);
        const endHour = parseInt(endTimeSelect.value.split(':')[0]);
        if (startHour < 4 || endHour > 23) {
            showToast('Tournament times must be between 4:00 AM and 11:00 PM', 'warning');
            return false;
        }

        // Create and set vote data JSON
        const voteData = {
            lake_id: parseInt(lakeSelect.value),
            ramp_id: parseInt(rampSelect.value),
            start_time: startTimeSelect.value,
            end_time: endTimeSelect.value
        };

        if (voteDataInput) {
            voteDataInput.value = JSON.stringify(voteData);
        }

        return true;
    }

    /**
     * Validate simple poll vote
     * @param {string|number} pollId - Poll ID
     * @param {string} context - Context: 'admin_own', 'admin_proxy', 'nonadmin'
     * @returns {boolean} True if valid
     * @private
     */
    validateSimpleVote(pollId, context) {
        // For simple polls, find the form and check that a radio option is selected
        // The form has data-poll-id attribute, and radio inputs have name="option_id"
        const form = document.querySelector('form[data-poll-id="' + pollId + '"][data-context="' + context + '"]');
        if (!form) {
            console.error('Form not found for poll ' + pollId + ' context ' + context);
            return true; // Let form submit naturally
        }

        const optionInputs = form.querySelectorAll('input[type="radio"][name="option_id"]');
        const selected = Array.from(optionInputs).some(input => input.checked);
        if (!selected) {
            showToast('Please select an option to vote for', 'warning');
            return false;
        }

        return true;
    }

    /**
     * Get element IDs for a poll based on context
     * @param {string|number} pollId - Poll ID
     * @param {string} context - Context: 'admin_own', 'admin_proxy', 'nonadmin'
     * @returns {Object} Object with element ID keys
     * @private
     */
    getElementIds(pollId, context) {
        const prefixes = {
            'admin_own': {
                lake: 'lake_select_admin_own_',
                ramp: 'ramp_select_admin_own_',
                startTime: 'start_time_admin_own_',
                endTime: 'end_time_admin_own_',
                voteData: 'vote_option_id_admin_own_'
            },
            'admin_proxy': {
                lake: 'admin_lake_select_',
                ramp: 'admin_ramp_select_',
                startTime: 'admin_start_time_',
                endTime: 'admin_end_time_',
                voteData: 'admin_vote_option_id_',
                member: 'vote_as_angler_'
            },
            'nonadmin': {
                lake: 'lake_select_nonadmin_',
                ramp: 'ramp_select_nonadmin_',
                startTime: 'start_time_nonadmin_',
                endTime: 'end_time_nonadmin_',
                voteData: 'vote_option_id_nonadmin_'
            }
        };

        const prefix = prefixes[context];
        const ids = {};

        for (const [key, idPrefix] of Object.entries(prefix)) {
            ids[key] = idPrefix + pollId;
        }

        return ids;
    }
}

// Export PollVotingHandler globally — consumed by polls-page.js
window.PollVotingHandler = PollVotingHandler;

// Also export for CommonJS environments (e.g. tests)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PollVotingHandler;
}
})();
