/**
 * Admin Merge Users page JavaScript functionality
 * Handles user merge preview and confirmation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Enable/disable execute button based on checkbox
    const confirmCheckbox = document.getElementById('confirm_checkbox');
    if (confirmCheckbox) {
        confirmCheckbox.addEventListener('change', function() {
            document.getElementById('execute_button').disabled = !this.checked;
        });
    }

    // Attach event listeners for preview loading
    const sourceSelect = document.getElementById('source_id');
    const targetSelect = document.getElementById('target_id');

    if (sourceSelect) {
        sourceSelect.addEventListener('change', loadPreview);
    }
    if (targetSelect) {
        targetSelect.addEventListener('change', loadPreview);
    }
});

/**
 * Load merge preview when both source and target accounts are selected
 * Fetches preview data from server and displays migration information
 * Shows loading indicator while fetching and handles errors appropriately
 */
function loadPreview() {
    const sourceId = document.getElementById('source_id').value;
    const targetId = document.getElementById('target_id').value;

    if (!sourceId || !targetId) {
        document.getElementById('preview_section').classList.add('d-none');
        return;
    }

    if (sourceId === targetId) {
        showToast('Source and target accounts must be different!', 'warning');
        return;
    }

    // Show preview section with loading indicator
    document.getElementById('preview_section').classList.remove('d-none');
    document.getElementById('preview_content').innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading preview...</span>
            </div>
            <p class="mt-3 text-muted">Loading preview...</p>
        </div>
    `;

    // Set form values
    document.getElementById('form_source_id').value = sourceId;
    document.getElementById('form_target_id').value = targetId;

    // Fetch preview data
    const formData = new FormData();
    formData.append('source_id', sourceId);
    formData.append('target_id', targetId);

    const csrfToken = getCsrfToken();

    fetch('/admin/users/merge/preview', {
        method: 'POST',
        headers: {
            'x-csrf-token': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderPreview(data.data);
        } else {
            document.getElementById('preview_content').innerHTML = `
                <div class="alert alert-danger">
                    <h5 class="alert-heading"><i class="bi bi-x-circle me-2"></i>Error</h5>
                    <p class="mb-0">${escapeHtml(data.error || 'Unknown error')}</p>
                </div>
            `;
        }
    })
    .catch(error => {
        document.getElementById('preview_content').innerHTML = `
            <div class="alert alert-danger">
                <h5 class="alert-heading"><i class="bi bi-x-circle me-2"></i>Error</h5>
                <p class="mb-0">Failed to load preview: ${escapeHtml(error.message || 'Unknown error')}</p>
            </div>
        `;
    });
}

/**
 * Render the merge preview data into HTML
 * Displays source/target accounts, duplicate vote warnings, and data counts
 * @param {Object} preview - Preview data from server
 * @param {Object} preview.source_angler - Source angler information
 * @param {string} preview.source_angler.name - Source angler name
 * @param {string} [preview.source_angler.email] - Source angler email
 * @param {Object} preview.target_angler - Target angler information
 * @param {string} preview.target_angler.name - Target angler name
 * @param {string} [preview.target_angler.email] - Target angler email
 * @param {Array<{poll_title: string}>} preview.duplicate_poll_votes - Polls where both accounts voted
 * @param {number} preview.results_count - Number of tournament results to migrate
 * @param {number} preview.team_results_angler1_count - Team results as angler 1
 * @param {number} preview.team_results_angler2_count - Team results as angler 2
 * @param {number} preview.poll_votes_count - Number of poll votes to migrate
 * @param {number} preview.officer_positions_count - Number of officer positions to migrate
 * @param {number} preview.polls_created_count - Number of polls created by source
 * @param {number} preview.news_authored_count - Number of news articles authored
 * @param {number} preview.tournaments_created_count - Number of tournaments created
 * @param {number} preview.proxy_votes_cast_count - Number of proxy votes cast
 */
function renderPreview(preview) {
    const duplicateVotesHtml = preview.duplicate_poll_votes.length > 0 ? `
        <div class="alert alert-warning border-warning mt-3">
            <h6 class="alert-heading"><i class="bi bi-exclamation-triangle-fill me-2"></i>Duplicate Poll Votes Detected</h6>
            <p class="mb-2">Both accounts have voted on the following polls. The source account's votes will be <strong>deleted</strong>:</p>
            <ul class="mb-0">
                ${preview.duplicate_poll_votes.map(dv => `<li>${escapeHtml(dv.poll_title || '')}</li>`).join('')}
            </ul>
        </div>
    ` : '';

    const html = `
        <div class="row g-3">
            <div class="col-md-6">
                <div class="card bg-secondary h-100">
                    <div class="card-body">
                        <h6 class="card-title text-danger"><i class="bi bi-database-dash me-2"></i>Data Moving FROM</h6>
                        <p class="mb-1"><strong>${escapeHtml(preview.source_angler.name || '')}</strong></p>
                        <p class="text-muted small mb-0">${escapeHtml(preview.source_angler.email || 'No email')}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-secondary h-100">
                    <div class="card-body">
                        <h6 class="card-title text-success"><i class="bi bi-database-add me-2"></i>Data Moving TO</h6>
                        <p class="mb-1"><strong>${escapeHtml(preview.target_angler.name || '')}</strong></p>
                        <p class="text-muted small mb-0">${escapeHtml(preview.target_angler.email || 'No email')}</p>
                    </div>
                </div>
            </div>
        </div>

        ${duplicateVotesHtml}

        <h6 class="mt-4 mb-3"><i class="bi bi-list-check me-2"></i>Data to be Migrated</h6>
        <div class="row g-3">
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-primary mb-1">${preview.results_count}</h3>
                    <small class="text-muted">Tournament Results</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-primary mb-1">${preview.team_results_angler1_count + preview.team_results_angler2_count}</h3>
                    <small class="text-muted">Team Results</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-primary mb-1">${preview.poll_votes_count}</h3>
                    <small class="text-muted">Poll Votes</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-primary mb-1">${preview.officer_positions_count}</h3>
                    <small class="text-muted">Officer Positions</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-muted mb-1">${preview.polls_created_count}</h3>
                    <small class="text-muted">Polls Created</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-muted mb-1">${preview.news_authored_count}</h3>
                    <small class="text-muted">News Articles</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-muted mb-1">${preview.tournaments_created_count}</h3>
                    <small class="text-muted">Tournaments Created</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center p-3 bg-secondary rounded">
                    <h3 class="text-muted mb-1">${preview.proxy_votes_cast_count}</h3>
                    <small class="text-muted">Proxy Votes Cast</small>
                </div>
            </div>
        </div>
    `;

    document.getElementById('preview_content').innerHTML = html;
}
