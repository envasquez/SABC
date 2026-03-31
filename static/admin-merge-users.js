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
        document.getElementById('preview_section').style.display = 'none';
        return;
    }

    if (sourceId === targetId) {
        showToast('Source and target accounts must be different!', 'warning');
        return;
    }

    // Show preview section with loading indicator
    document.getElementById('preview_section').style.display = '';
    document.getElementById('preview_content').innerHTML = `
        <div style="text-align:center;padding:2.5rem 0">
            <div class="spinner-border" style="color:var(--brand)" role="status">
                <span class="visually-hidden">Loading preview...</span>
            </div>
            <p style="margin-top:.75rem;color:var(--t3)">Loading preview...</p>
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
                <div style="padding:1rem;border-radius:var(--r-md);background:var(--err-m);color:var(--err);font-size:.85rem;border:1px solid color-mix(in srgb,var(--err) 25%,transparent)">
                    <div style="font-weight:700;margin-bottom:.35rem"><i class="bi bi-x-circle"></i> Error</div>
                    <p style="margin:0">${escapeHtml(data.error || 'Unknown error')}</p>
                </div>
            `;
        }
    })
    .catch(error => {
        document.getElementById('preview_content').innerHTML = `
            <div style="padding:1rem;border-radius:var(--r-md);background:var(--err-m);color:var(--err);font-size:.85rem;border:1px solid color-mix(in srgb,var(--err) 25%,transparent)">
                <div style="font-weight:700;margin-bottom:.35rem"><i class="bi bi-x-circle"></i> Error</div>
                <p style="margin:0">Failed to load preview: ${escapeHtml(error.message || 'Unknown error')}</p>
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
        <div style="padding:.75rem 1rem;border-radius:var(--r-md);background:var(--warn-m);color:var(--warn);font-size:.85rem;margin-top:.75rem;border:1px solid color-mix(in srgb,var(--warn) 25%,transparent)">
            <div style="font-weight:700;margin-bottom:.35rem"><i class="bi bi-exclamation-triangle-fill"></i> Duplicate Poll Votes Detected</div>
            <p style="margin-bottom:.35rem">Both accounts have voted on the following polls. The source account's votes will be <strong>deleted</strong>:</p>
            <ul style="margin:0;padding-left:1.25rem">
                ${preview.duplicate_poll_votes.map(dv => `<li>${escapeHtml(dv.poll_title || '')}</li>`).join('')}
            </ul>
        </div>
    ` : '';

    const html = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
            <div style="padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-weight:600;color:var(--err);font-size:.88rem;margin-bottom:.35rem"><i class="bi bi-database-dash"></i> Data Moving FROM</div>
                <p style="margin-bottom:.15rem;color:var(--t1)"><strong>${escapeHtml(preview.source_angler.name || '')}</strong></p>
                <p style="color:var(--t3);font-size:.8rem;margin:0">${escapeHtml(preview.source_angler.email || 'No email')}</p>
            </div>
            <div style="padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-weight:600;color:var(--ok);font-size:.88rem;margin-bottom:.35rem"><i class="bi bi-database-add"></i> Data Moving TO</div>
                <p style="margin-bottom:.15rem;color:var(--t1)"><strong>${escapeHtml(preview.target_angler.name || '')}</strong></p>
                <p style="color:var(--t3);font-size:.8rem;margin:0">${escapeHtml(preview.target_angler.email || 'No email')}</p>
            </div>
        </div>

        ${duplicateVotesHtml}

        <div style="font-weight:600;font-size:.88rem;color:var(--t1);margin-top:1.25rem;margin-bottom:.75rem"><i class="bi bi-list-check"></i> Data to be Migrated</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem">
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--brand);margin-bottom:.15rem">${preview.results_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Tournament Results</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--brand);margin-bottom:.15rem">${preview.team_results_angler1_count + preview.team_results_angler2_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Team Results</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--brand);margin-bottom:.15rem">${preview.poll_votes_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Poll Votes</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--brand);margin-bottom:.15rem">${preview.officer_positions_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Officer Positions</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--t3);margin-bottom:.15rem">${preview.polls_created_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Polls Created</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--t3);margin-bottom:.15rem">${preview.news_authored_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">News Articles</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--t3);margin-bottom:.15rem">${preview.tournaments_created_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Tournaments Created</div>
            </div>
            <div style="text-align:center;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md)">
                <div style="font-size:1.5rem;font-weight:700;color:var(--t3);margin-bottom:.15rem">${preview.proxy_votes_cast_count}</div>
                <div style="font-size:.75rem;color:var(--t3)">Proxy Votes Cast</div>
            </div>
        </div>
    `;

    document.getElementById('preview_content').innerHTML = html;
}
