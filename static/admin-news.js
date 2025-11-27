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
            editNews(id, title, content, priority);
        });
    });

    // Delete button event listeners
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const title = this.dataset.title;
            deleteNews(id, title);
        });
    });
});

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
        body: formData
    })
    .then(response => {
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            return response.text().then(text => {
                throw new Error('Failed to send test email');
            });
        }
    })
    .catch(error => {
        showToast('Error sending test email: ' + error.message, 'error');
    });
}

function editNews(id, title, content, priority) {
    // Set form action
    document.getElementById('editForm').action = `/admin/news/${id}/update`;

    // Fill form fields
    document.getElementById('edit_title').value = title;
    document.getElementById('edit_content').value = content;
    document.getElementById('edit_priority').value = priority;

    // Show modal
    showModal('editModal');
}

function deleteNews(id, title) {
    newsDeleteManager.confirm(id, title);
}
