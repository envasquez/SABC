/**
 * Admin News page JavaScript functionality
 * Handles news CRUD operations, edit modal, and delete confirmation
 */

// Initialize delete confirmation manager
let newsDeleteManager;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize delete confirmation manager
    newsDeleteManager = new DeleteConfirmationManager({
        modalId: 'deleteNewsModal',
        itemNameElementId: 'delete-news-title',
        confirmInputId: 'delete-confirmation',
        confirmButtonId: 'confirmDeleteNewsBtn',
        deleteUrlTemplate: (id) => `/admin/news/${id}`,
        onSuccess: () => location.reload(),
        onError: (error) => showToast(`Error deleting news: ${error}`, 'error')
    });

    // Edit button event listeners
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const title = this.dataset.title;
            const content = this.dataset.content;
            const priority = this.dataset.priority;
            const autoArchiveAt = this.dataset.autoArchiveAt;
            editNews(id, title, content, priority, autoArchiveAt);
        });
    });

    // Set default auto-archive date for create form (30 days from now)
    const createAutoArchiveInput = document.getElementById('create_auto_archive_at');
    if (createAutoArchiveInput && !createAutoArchiveInput.value) {
        const defaultDate = new Date();
        defaultDate.setDate(defaultDate.getDate() + 30);
        createAutoArchiveInput.value = defaultDate.toISOString().split('T')[0];
    }

    // Delete button event listeners
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const title = this.dataset.title;
            deleteNews(id, title);
        });
    });

    // Submit confirmation for create/edit forms
    setupNewsConfirmation();
});

let pendingNewsForm = null;
let newsConfirmModal = null;

function setupNewsConfirmation() {
    const modalEl = document.getElementById('newsConfirmModal');
    if (!modalEl) return;
    newsConfirmModal = new bootstrap.Modal(modalEl);

    document.querySelectorAll('form[data-news-confirm]').forEach(form => {
        form.addEventListener('submit', (e) => {
            if (form.dataset.confirmed === 'true') return;
            e.preventDefault();

            const title = form.querySelector('[name="title"]')?.value?.trim() || '';
            const content = form.querySelector('[name="content"]')?.value?.trim() || '';

            if (!title) {
                showToast('Title is required', 'warning');
                return;
            }
            if (!content) {
                showToast('Content is required', 'warning');
                return;
            }

            const mode = form.dataset.newsConfirm;
            const priority = form.querySelector('[name="priority"]')?.value || '0';
            const archive = form.querySelector('[name="auto_archive_at"]')?.value || '';

            populateNewsConfirm(mode, title, content, priority, archive);
            pendingNewsForm = form;
            newsConfirmModal.show();
        });
    });

    document.getElementById('confirmNewsBtn')?.addEventListener('click', () => {
        if (!pendingNewsForm) return;
        const form = pendingNewsForm;
        pendingNewsForm = null;
        form.dataset.confirmed = 'true';
        newsConfirmModal.hide();
        form.submit();
    });

    modalEl.addEventListener('hidden.bs.modal', () => {
        if (pendingNewsForm && pendingNewsForm.dataset.confirmed !== 'true') {
            pendingNewsForm = null;
        }
    });
}

function populateNewsConfirm(mode, title, content, priority, archive) {
    const heading = document.getElementById('newsConfirmHeading');
    const btnText = document.getElementById('confirmNewsBtnText');
    const note = document.getElementById('newsConfirmNote');
    const titleEl = document.getElementById('newsConfirmTitle');
    const summary = document.getElementById('newsConfirmSummary');

    heading.textContent = mode === 'edit' ? 'Confirm Update' : 'Confirm Publish';
    btnText.textContent = mode === 'edit' ? 'Save Changes' : 'Publish';

    if (mode === 'create') {
        note.style.display = '';
        note.innerHTML = '<i class="bi bi-envelope" style="margin-right:.35rem"></i>All members will be emailed when this is published.';
    } else {
        note.style.display = 'none';
    }

    const priorityLabel = {'0': 'Normal', '1': 'High', '2': 'Urgent'}[priority] || 'Normal';

    titleEl.textContent = title;

    let html = '<dl class="row mb-0" style="margin:0">';
    html += '<dt class="col-sm-3"><i class="bi bi-card-text me-1"></i>Content</dt>';
    html += '<dd class="col-sm-9" style="white-space:pre-wrap;word-break:break-word">' + escapeHtml(content) + '</dd>';
    html += '<dt class="col-sm-3"><i class="bi bi-flag me-1"></i>Priority</dt>';
    html += '<dd class="col-sm-9 fw-bold">' + escapeHtml(priorityLabel) + '</dd>';
    if (archive) {
        html += '<dt class="col-sm-3"><i class="bi bi-archive me-1"></i>Auto Archive</dt>';
        html += '<dd class="col-sm-9">' + escapeHtml(archive) + '</dd>';
    }
    html += '</dl>';
    summary.innerHTML = html;
}

function sendTestEmail() {
    const title = document.getElementById('title').value;
    const content = document.getElementById('content').value;

    if (!title || !content) {
        showToast('Please fill in both title and content before sending a test email', 'warning');
        return;
    }

    if (!confirm('Send a test email to yourself with this content?')) {
        return;
    }

    // Create form data with CSRF token
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    formData.append('csrf_token', getCsrfToken());

    // Send test email
    fetch('/admin/news/test-email', {
        method: 'POST',
        credentials: 'same-origin',
        body: formData
    })
    .then(response => {
        if (!response.ok && !response.redirected) {
            throw new Error(`Server error: ${response.status}`);
        }
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            // Success without redirect - show success message
            showToast('Test email sent successfully!', 'success');
        }
    })
    .catch(error => {
        showToast('Error sending test email: ' + error.message, 'error');
    });
}

function editNews(id, title, content, priority, autoArchiveAt) {
    // Set form action
    document.getElementById('editForm').action = `/admin/news/${id}/update`;

    // Fill form fields
    document.getElementById('edit_title').value = title;
    document.getElementById('edit_content').value = content;
    document.getElementById('edit_priority').value = priority;
    document.getElementById('edit_auto_archive_at').value = autoArchiveAt || '';

    // Show modal
    showModal('editModal');
}

function deleteNews(id, title) {
    newsDeleteManager.confirm(id, title);
}
