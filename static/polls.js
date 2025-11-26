/**
 * SABC Poll Voting Handler
 * Centralized voting logic for all poll types
 */

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
                if (!this.validateVoteForm(form)) {
                    e.preventDefault();
                    return false;
                }
            });
        });
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

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PollVotingHandler;
}
