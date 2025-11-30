/**
 * Tournament Results Entry - JavaScript Module
 * Handles autocomplete, team management, and result submission for tournament results entry page
 */

// Module state - encapsulated to avoid global namespace pollution
const ResultsEntryState = {
    teamCount: 0,
    anglers: [],
    existingAnglerIds: new Set(),
    editData: null,
    editTeamResultData: null,
    tournamentId: null
};

/**
 * Initialize the results entry page
 * @param {Object} config - Configuration object with anglers, existing IDs, edit data, and tournament ID
 */
function initializeResultsEntry(config) {
    ResultsEntryState.anglers = config.anglers || [];
    ResultsEntryState.existingAnglerIds = new Set(config.existingAnglerIds || []);
    ResultsEntryState.editData = config.editData || null;
    ResultsEntryState.editTeamResultData = config.editTeamResultData || null;
    ResultsEntryState.tournamentId = config.tournamentId;

    // Initialize form submission handler
    const form = document.getElementById('resultsForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Add first team on page load
    const editData = ResultsEntryState.editData;
    const editTeamResultData = ResultsEntryState.editTeamResultData;
    if (editData) {
        if (editData.type === 'individual') {
            addTeamForEdit(editData.angler_id, editData.angler_name, null, null,
                         editData.num_fish, editData.total_weight, editData.big_bass_weight,
                         editData.dead_fish_penalty, editData.disqualified, editData.buy_in, editData.was_member,
                         0, 0, 0, 0, false, false, true);
        } else if (editData.type === 'team') {
            let angler1_result = editData.angler1_result || [0, 0, 0, 0, false, false, true];
            let angler2_result = editData.angler2_result || [0, 0, 0, 0, false, false, true];
            addTeamForEdit(editData.angler1_id, editData.angler1_name, editData.angler2_id, editData.angler2_name,
                         angler1_result[0], angler1_result[1], angler1_result[2], angler1_result[3], angler1_result[4], angler1_result[5], angler1_result[6],
                         angler2_result[0], angler2_result[1], angler2_result[2], angler2_result[3], angler2_result[4], angler2_result[5], angler2_result[6]);
        }
    } else if (editTeamResultData) {
        // Edit team result mode - show one pre-loaded team
        addTeamForEdit(
            editTeamResultData.angler1_id, editTeamResultData.angler1_name,
            editTeamResultData.angler2_id, editTeamResultData.angler2_name,
            editTeamResultData.angler1_fish || 0,
            editTeamResultData.angler1_weight || 0,
            editTeamResultData.angler1_big_bass || 0,
            editTeamResultData.angler1_dead_penalty || 0,
            editTeamResultData.angler1_disqualified || false,
            editTeamResultData.angler1_buy_in || false,
            editTeamResultData.angler1_was_member !== false,
            editTeamResultData.angler2_fish || 0,
            editTeamResultData.angler2_weight || 0,
            editTeamResultData.angler2_big_bass || 0,
            editTeamResultData.angler2_dead_penalty || 0,
            editTeamResultData.angler2_disqualified || false,
            editTeamResultData.angler2_buy_in || false,
            editTeamResultData.angler2_was_member !== false
        );

        // Update the form action to edit instead of create
        const form = document.getElementById('resultsForm');
        if (form) {
            form.action = `/admin/tournaments/${ResultsEntryState.tournamentId}/team-results`;
            // Add hidden field for team result ID
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'team_result_id';
            hiddenInput.value = editTeamResultData.id;
            form.appendChild(hiddenInput);
        }

        // Hide the "Add Team" button since we're editing one specific team
        const addTeamBtn = document.querySelector('button[onclick="addTeam()"]');
        if (addTeamBtn) addTeamBtn.style.display = 'none';
    } else {
        // Default mode - add empty team
        addTeam();
    }
    updateAllAnglerDropdowns();
}

// ===== Autocomplete functionality =====

/**
 * Setup autocomplete for an input field
 * @param {HTMLInputElement} input - The input element to setup autocomplete for
 */
function setupAutocomplete(input) {
    const wrapper = input.closest('.autocomplete-wrapper');
    const dropdown = wrapper.querySelector('.autocomplete-dropdown');
    const hiddenInput = wrapper.querySelector('input[type="hidden"]');
    const clearBtn = wrapper.querySelector('.clear-selection');
    let selectedIndex = -1;

    input.addEventListener('input', function() {
        const query = this.value.toLowerCase().trim();

        if (!query) {
            dropdown.style.display = 'none';
            hiddenInput.value = '';
            clearBtn.style.display = 'none';
            input.classList.remove('angler-selected');
            return;
        }

        // Filter anglers
        const matches = ResultsEntryState.anglers.filter(a =>
            a.name.toLowerCase().includes(query)
        );

        if (matches.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-no-results">No anglers found</div>';
            dropdown.style.display = 'block';
            return;
        }

        // Show dropdown with matches
        dropdown.innerHTML = matches.map((angler, idx) =>
            `<div class="autocomplete-item" data-id="${angler.id}" data-name="${escapeHtml(angler.name)}" data-idx="${idx}">
                ${escapeHtml(angler.name)}
            </div>`
        ).join('');
        dropdown.style.display = 'block';
        selectedIndex = -1;

        // Add click handlers
        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', function() {
                selectAngler(this.dataset.id, this.dataset.name, input, hiddenInput, dropdown, clearBtn);
            });
        });
    });

    // Keyboard navigation
    input.addEventListener('keydown', function(e) {
        const items = dropdown.querySelectorAll('.autocomplete-item');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            updateSelection(items, selectedIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, 0);
            updateSelection(items, selectedIndex);
        } else if (e.key === 'Enter' && selectedIndex >= 0) {
            e.preventDefault();
            const selected = items[selectedIndex];
            if (selected) {
                selectAngler(selected.dataset.id, selected.dataset.name, input, hiddenInput, dropdown, clearBtn);
            }
        } else if (e.key === 'Escape') {
            dropdown.style.display = 'none';
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!wrapper.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function updateSelection(items, index) {
    items.forEach((item, idx) => {
        item.classList.toggle('active', idx === index);
    });
    if (items[index]) {
        items[index].scrollIntoView({ block: 'nearest' });
    }
}

function selectAngler(id, name, input, hiddenInput, dropdown, clearBtn) {
    input.value = name;
    hiddenInput.value = id;
    input.classList.add('angler-selected');
    clearBtn.style.display = 'block';
    dropdown.style.display = 'none';
    onAnglerChange();
}

function clearAnglerSelection(teamId, anglerNum) {
    const wrapper = document.querySelector(`[data-team="${teamId}"][data-angler="${anglerNum}"]`).closest('.autocomplete-wrapper');
    const input = wrapper.querySelector('.autocomplete-input');
    const hiddenInput = wrapper.querySelector('input[type="hidden"]');
    const clearBtn = wrapper.querySelector('.clear-selection');

    input.value = '';
    hiddenInput.value = '';
    input.classList.remove('angler-selected');
    clearBtn.style.display = 'none';
    onAnglerChange();
}

// ===== Team Management =====

/**
 * Add a new empty team to the form
 */
function addTeam() {
    ResultsEntryState.teamCount++;
    const teamCount = ResultsEntryState.teamCount;
    const container = document.getElementById('teams-container');

    const teamHtml = `
        <div class="card mb-3 team-card" id="team-${teamCount}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Team ${teamCount}</h6>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeTeam(${teamCount})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="card-body">
                <div class="row">
                    <!-- Angler 1 -->
                    <div class="col-md-6">
                        <h6 class="text-primary">Boater</h6>
                        <div class="row g-2">
                            <div class="col-12">
                                <label class="form-label">Name</label>
                                <div class="autocomplete-wrapper">
                                    <input type="text"
                                           class="form-control autocomplete-input angler1-input"
                                           data-team="${teamCount}"
                                           data-angler="1"
                                           placeholder="Start typing angler name..."
                                           autocomplete="off"
                                           required>
                                    <span class="clear-selection" style="display:none;" onclick="clearAnglerSelection(${teamCount}, 1)">×</span>
                                    <div class="autocomplete-dropdown"></div>
                                    <input type="hidden" name="angler1_id_${teamCount}" class="angler1-id">
                                </div>
                            </div>
                            <div class="col-4">
                                <label class="form-label">Fish</label>
                                <input type="number" class="form-control" name="angler1_fish_${teamCount}" min="0" max="5" value="0">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Weight (lbs)</label>
                                <input type="number" class="form-control" name="angler1_weight_${teamCount}" step="0.01" min="0" value="0.00">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Big Bass (lbs)</label>
                                <input type="number" class="form-control" name="angler1_big_bass_${teamCount}" step="0.01" min="0" value="0.00">
                            </div>
                            <div class="col-6">
                                <label class="form-label">Dead Fish Penalty</label>
                                <input type="number" class="form-control" name="angler1_dead_penalty_${teamCount}" step="0.25" min="0" value="0.00">
                            </div>
                            <div class="col-6">
                                <div class="form-check mt-4">
                                    <input class="form-check-input" type="checkbox" name="angler1_disqualified_${teamCount}" value="1">
                                    <label class="form-check-label">Disqualified</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler1_buyIn_${teamCount}" value="1" onchange="handleBuyInChange(this, ${teamCount}, 'angler1')">
                                    <label class="form-label">Buy-in</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler1_was_member_${teamCount}" value="1" checked>
                                    <label class="form-check-label">Member</label>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Angler 2 -->
                    <div class="col-md-6">
                        <h6 class="text-primary">Non-boater</h6>
                        <div class="row g-2">
                            <div class="col-12">
                                <label class="form-label">Name <span class="text-secondary">(optional)</span></label>
                                <div class="autocomplete-wrapper">
                                    <input type="text"
                                           class="form-control autocomplete-input angler2-input"
                                           data-team="${teamCount}"
                                           data-angler="2"
                                           placeholder="Start typing angler name..."
                                           autocomplete="off">
                                    <span class="clear-selection" style="display:none;" onclick="clearAnglerSelection(${teamCount}, 2)">×</span>
                                    <div class="autocomplete-dropdown"></div>
                                    <input type="hidden" name="angler2_id_${teamCount}" class="angler2-id">
                                </div>
                            </div>
                            <div class="col-4">
                                <label class="form-label">Fish</label>
                                <input type="number" class="form-control" name="angler2_fish_${teamCount}" min="0" max="5" value="0">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Weight (lbs)</label>
                                <input type="number" class="form-control" name="angler2_weight_${teamCount}" step="0.01" min="0" value="0.00">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Big Bass (lbs)</label>
                                <input type="number" class="form-control" name="angler2_big_bass_${teamCount}" step="0.01" min="0" value="0.00">
                            </div>
                            <div class="col-6">
                                <label class="form-label">Dead Fish Penalty</label>
                                <input type="number" class="form-control" name="angler2_dead_penalty_${teamCount}" step="0.25" min="0" value="0.00">
                            </div>
                            <div class="col-6">
                                <div class="form-check mt-4">
                                    <input class="form-check-input" type="checkbox" name="angler2_disqualified_${teamCount}" value="1">
                                    <label class="form-check-label">Disqualified</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler2_buyIn_${teamCount}" value="1" onchange="handleBuyInChange(this, ${teamCount}, 'angler2')">
                                    <label class="form-check-label">Buy-in</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler2_was_member_${teamCount}" value="1" checked>
                                    <label class="form-check-label">Member</label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', teamHtml);

    // Setup autocomplete for the newly added team
    const teamCard = document.getElementById(`team-${teamCount}`);
    teamCard.querySelectorAll('.autocomplete-input').forEach(input => {
        setupAutocomplete(input);
    });

    // Update all dropdowns to reflect newly selected anglers
    updateAllAnglerDropdowns();
}

/**
 * Remove a team from the form
 * @param {number} teamNumber - The team number to remove
 */
function removeTeam(teamNumber) {
    const teamCard = document.getElementById(`team-${teamNumber}`);
    if (teamCard) {
        teamCard.remove();
        // Update all dropdowns after removing a team
        updateAllAnglerDropdowns();
    }
}

/**
 * Add a team with pre-filled data (for edit mode)
 */
function addTeamForEdit(angler1_id, angler1_name, angler2_id, angler2_name,
                       angler1_fish, angler1_weight, angler1_big_bass, angler1_dead_penalty, angler1_disqualified, angler1_buy_in, angler1_was_member,
                       angler2_fish, angler2_weight, angler2_big_bass, angler2_dead_penalty, angler2_disqualified, angler2_buy_in, angler2_was_member) {
    ResultsEntryState.teamCount++;
    const teamCount = ResultsEntryState.teamCount;
    const container = document.getElementById('teams-container');

    const teamHtml = `
        <div class="card mb-3 team-card" id="team-${teamCount}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Team ${teamCount}</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6 class="text-primary">Boater</h6>
                        <div class="row g-2">
                            <div class="col-12">
                                <label class="form-label">Name</label>
                                <div class="autocomplete-wrapper">
                                    <input type="text"
                                           class="form-control autocomplete-input angler1-input"
                                           data-team="${teamCount}"
                                           data-angler="1"
                                           placeholder="Start typing angler name..."
                                           autocomplete="off"
                                           value="${escapeHtml(angler1_name)}"
                                           required>
                                    <span class="clear-selection" style="display:${angler1_id ? 'block' : 'none'};" onclick="clearAnglerSelection(${teamCount}, 1)">×</span>
                                    <div class="autocomplete-dropdown"></div>
                                    <input type="hidden" name="angler1_id_${teamCount}" class="angler1-id" value="${angler1_id}">
                                </div>
                            </div>
                            <div class="col-4">
                                <label class="form-label">Fish</label>
                                <input type="number" class="form-control" name="angler1_fish_${teamCount}" min="0" max="5" value="${angler1_fish}">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Weight (lbs)</label>
                                <input type="number" class="form-control" name="angler1_weight_${teamCount}" step="0.01" min="0" value="${angler1_weight}">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Big Bass (lbs)</label>
                                <input type="number" class="form-control" name="angler1_big_bass_${teamCount}" step="0.01" min="0" value="${angler1_big_bass}">
                            </div>
                            <div class="col-6">
                                <label class="form-label">Dead Fish Penalty</label>
                                <input type="number" class="form-control" name="angler1_dead_penalty_${teamCount}" step="0.25" min="0" value="${angler1_dead_penalty}">
                            </div>
                            <div class="col-6">
                                <div class="form-check mt-4">
                                    <input class="form-check-input" type="checkbox" name="angler1_disqualified_${teamCount}" value="1" ${angler1_disqualified ? 'checked' : ''}>
                                    <label class="form-check-label">Disqualified</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler1_buyIn_${teamCount}" value="1" ${angler1_buy_in ? 'checked' : ''} onchange="handleBuyInChange(this, ${teamCount}, 'angler1')">
                                    <label class="form-check-label">Buy-in</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler1_was_member_${teamCount}" value="1" ${angler1_was_member !== false ? 'checked' : ''}>
                                    <label class="form-check-label">Member</label>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <h6 class="text-primary">Non-boater</h6>
                        <div class="row g-2">
                            <div class="col-12">
                                <label class="form-label">Name <span class="text-secondary">(optional)</span></label>
                                <div class="autocomplete-wrapper">
                                    <input type="text"
                                           class="form-control autocomplete-input angler2-input"
                                           data-team="${teamCount}"
                                           data-angler="2"
                                           placeholder="Start typing angler name..."
                                           autocomplete="off"
                                           value="${angler2_name ? escapeHtml(angler2_name) : ''}">
                                    <span class="clear-selection" style="display:${angler2_id ? 'block' : 'none'};" onclick="clearAnglerSelection(${teamCount}, 2)">×</span>
                                    <div class="autocomplete-dropdown"></div>
                                    <input type="hidden" name="angler2_id_${teamCount}" class="angler2-id" value="${angler2_id || ''}">
                                </div>
                            </div>
                            <div class="col-4">
                                <label class="form-label">Fish</label>
                                <input type="number" class="form-control" name="angler2_fish_${teamCount}" min="0" max="5" value="${angler2_fish}">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Weight (lbs)</label>
                                <input type="number" class="form-control" name="angler2_weight_${teamCount}" step="0.01" min="0" value="${angler2_weight}">
                            </div>
                            <div class="col-4">
                                <label class="form-label">Big Bass (lbs)</label>
                                <input type="number" class="form-control" name="angler2_big_bass_${teamCount}" step="0.01" min="0" value="${angler2_big_bass}">
                            </div>
                            <div class="col-6">
                                <label class="form-label">Dead Fish Penalty</label>
                                <input type="number" class="form-control" name="angler2_dead_penalty_${teamCount}" step="0.25" min="0" value="${angler2_dead_penalty}">
                            </div>
                            <div class="col-6">
                                <div class="form-check mt-4">
                                    <input class="form-check-input" type="checkbox" name="angler2_disqualified_${teamCount}" value="1" ${angler2_disqualified ? 'checked' : ''}>
                                    <label class="form-check-label">Disqualified</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler2_buyIn_${teamCount}" value="1" ${angler2_buy_in ? 'checked' : ''} onchange="handleBuyInChange(this, ${teamCount}, 'angler2')">
                                    <label class="form-check-label">Buy-in</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="angler2_was_member_${teamCount}" value="1" ${angler2_was_member !== false ? 'checked' : ''}>
                                    <label class="form-check-label">Member</label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', teamHtml);

    // Setup autocomplete for the newly added team
    const teamCard = document.getElementById(`team-${teamCount}`);
    teamCard.querySelectorAll('.autocomplete-input').forEach(input => {
        setupAutocomplete(input);
        // If there's a pre-selected value, mark it as selected
        if (input.value) {
            input.classList.add('angler-selected');
        }
    });
}

// Handle Buy-in checkbox changes - zero out results when Buy-in is checked
function handleBuyInChange(checkbox, teamNumber, anglerType) {
    const isChecked = checkbox.checked;

    if (isChecked) {
        // Zero out all results for this angler when Buy-in is selected
        const fishInput = document.querySelector(`[name="${anglerType}_fish_${teamNumber}"]`);
        const weightInput = document.querySelector(`[name="${anglerType}_weight_${teamNumber}"]`);
        const bigBassInput = document.querySelector(`[name="${anglerType}_big_bass_${teamNumber}"]`);
        const deadPenaltyInput = document.querySelector(`[name="${anglerType}_dead_penalty_${teamNumber}"]`);

        if (fishInput) fishInput.value = '0';
        if (weightInput) weightInput.value = '0.00';
        if (bigBassInput) bigBassInput.value = '0.00';
        if (deadPenaltyInput) deadPenaltyInput.value = '0.00';

        // Disable the inputs to prevent editing
        if (fishInput) fishInput.disabled = true;
        if (weightInput) weightInput.disabled = true;
        if (bigBassInput) bigBassInput.disabled = true;
        if (deadPenaltyInput) deadPenaltyInput.disabled = true;
    } else {
        // Re-enable inputs when Buy-in is unchecked
        const fishInput = document.querySelector(`[name="${anglerType}_fish_${teamNumber}"]`);
        const weightInput = document.querySelector(`[name="${anglerType}_weight_${teamNumber}"]`);
        const bigBassInput = document.querySelector(`[name="${anglerType}_big_bass_${teamNumber}"]`);
        const deadPenaltyInput = document.querySelector(`[name="${anglerType}_dead_penalty_${teamNumber}"]`);

        if (fishInput) fishInput.disabled = false;
        if (weightInput) weightInput.disabled = false;
        if (bigBassInput) bigBassInput.disabled = false;
        if (deadPenaltyInput) deadPenaltyInput.disabled = false;
    }
}

// ===== Guest Creation =====

/**
 * Show the create guest modal
 */
function showCreateGuestModal() {
    const modal = new bootstrap.Modal(document.getElementById('createGuestModal'));
    modal.show();
}

/**
 * Create a new guest user
 */
function createGuest() {
    const name = document.getElementById('guestName').value.trim();
    const email = document.getElementById('guestEmail').value.trim();
    const phone = document.getElementById('guestPhone').value.trim();

    if (!name) {
        showToast('Guest name is required', 'warning');
        return;
    }

    // Prepare the data
    const guestData = {
        name: name,
        email: email || null,
        phone: phone || null,
        member: false
    };

    // Send request to create guest
    fetch('/admin/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-csrf-token': getCsrfToken(),
        },
        body: JSON.stringify(guestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Add the new guest to the anglers array
            ResultsEntryState.anglers.push({
                id: data.angler_id,
                name: name
            });

            // Update all dropdowns
            updateAllAnglerDropdowns();

            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createGuestModal'));
            modal.hide();

            // Clear the form
            document.getElementById('createGuestForm').reset();

            showToast(`Guest "${name}" created successfully!`, 'success');
        } else {
            showToast('Error creating guest: ' + (data.message || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error creating guest. Please try again.', 'error');
    });
}

// ===== Form Submission =====

/**
 * Handle form submission to save individual results
 * @param {Event} e - Submit event
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const teams = document.querySelectorAll('.team-card');

    try {
        for (const team of teams) {
            const teamId = team.id.replace('team-', '');

            // Save angler1 (boater) result
            const angler1Id = formData.get(`angler1_id_${teamId}`);
            console.log(`Team ${teamId}: angler1_id =`, angler1Id);
            if (angler1Id) {
                const angler1Data = new FormData();
                angler1Data.append('csrf_token', formData.get('csrf_token'));
                angler1Data.append('angler_id', angler1Id);
                angler1Data.append('num_fish', formData.get(`angler1_fish_${teamId}`) || 0);
                angler1Data.append('total_weight', formData.get(`angler1_weight_${teamId}`) || 0);
                angler1Data.append('big_bass_weight', formData.get(`angler1_big_bass_${teamId}`) || 0);
                angler1Data.append('dead_fish', formData.get(`angler1_dead_penalty_${teamId}`) || 0);
                angler1Data.append('disqualified', formData.get(`angler1_disqualified_${teamId}`) ? 'on' : '');
                angler1Data.append('buy_in', formData.get(`angler1_buyIn_${teamId}`) ? 'on' : '');
                angler1Data.append('was_member', formData.get(`angler1_was_member_${teamId}`) ? 'on' : '');

                const response1 = await fetch(`/admin/tournaments/${ResultsEntryState.tournamentId}/results`, {
                    method: 'POST',
                    body: angler1Data,
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!response1.ok) {
                    const errorText = await response1.text();
                    console.error('Angler 1 save failed:', response1.status, errorText);
                    throw new Error(`Failed to save angler 1 result: ${response1.status}`);
                }
            }

            // Save angler2 (co-angler) result if exists
            const angler2Id = formData.get(`angler2_id_${teamId}`);
            console.log(`Team ${teamId}: angler2_id =`, angler2Id);
            if (angler2Id) {
                const angler2Data = new FormData();
                angler2Data.append('csrf_token', formData.get('csrf_token'));
                angler2Data.append('angler_id', angler2Id);
                angler2Data.append('num_fish', formData.get(`angler2_fish_${teamId}`) || 0);
                angler2Data.append('total_weight', formData.get(`angler2_weight_${teamId}`) || 0);
                angler2Data.append('big_bass_weight', formData.get(`angler2_big_bass_${teamId}`) || 0);
                angler2Data.append('dead_fish', formData.get(`angler2_dead_penalty_${teamId}`) || 0);
                angler2Data.append('disqualified', formData.get(`angler2_disqualified_${teamId}`) ? 'on' : '');
                angler2Data.append('buy_in', formData.get(`angler2_buyIn_${teamId}`) ? 'on' : '');
                angler2Data.append('was_member', formData.get(`angler2_was_member_${teamId}`) ? 'on' : '');

                const response2 = await fetch(`/admin/tournaments/${ResultsEntryState.tournamentId}/results`, {
                    method: 'POST',
                    body: angler2Data,
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!response2.ok) {
                    const errorText = await response2.text();
                    console.error('Angler 2 save failed:', response2.status, errorText);
                    throw new Error(`Failed to save angler 2 result: ${response2.status}`);
                }
            }

            // Save team result (works for solo or team)
            if (angler1Id) {
                const teamData = new FormData();
                teamData.append('csrf_token', formData.get('csrf_token'));
                teamData.append('angler1_id', angler1Id);
                if (angler2Id) {
                    teamData.append('angler2_id', angler2Id);
                }

                const teamResponse = await fetch(`/admin/tournaments/${ResultsEntryState.tournamentId}/team-results`, {
                    method: 'POST',
                    body: teamData,
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!teamResponse.ok) {
                    const errorText = await teamResponse.text();
                    console.error('Team result save failed:', teamResponse.status, errorText);
                    throw new Error(`Failed to save team result: ${teamResponse.status}`);
                }
            }
        }

        // Success - redirect to tournament view
        window.location.href = `/tournaments/${ResultsEntryState.tournamentId}`;
    } catch (error) {
        console.error('Error saving results:', error);
        showToast('Error saving results. Please try again.', 'error');
    }
}

// Make functions available globally for onclick handlers
window.addTeam = addTeam;
window.removeTeam = removeTeam;
window.clearAnglerSelection = clearAnglerSelection;
window.handleBuyInChange = handleBuyInChange;
window.showCreateGuestModal = showCreateGuestModal;
window.createGuest = createGuest;
window.initializeResultsEntry = initializeResultsEntry;
