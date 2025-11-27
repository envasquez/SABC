/**
 * Admin News page JavaScript functionality
 * Handles news CRUD operations, edit modal, and delete confirmation
 */

let deleteNewsId = null;

document.addEventListener('DOMContentLoaded', function() {
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
    // Set the news info in the modal
    deleteNewsId = id;
    document.getElementById('delete-news-title').textContent = title;
    document.getElementById('delete-confirmation').value = '';

    // Show the modal
    showModal('deleteNewsModal');
}

async function confirmDeleteNews() {
    const confirmText = document.getElementById('delete-confirmation').value;

    if (confirmText.trim() !== 'DELETE') {
        showToast('Please type DELETE to confirm', 'warning');
        return;
    }

    // Close the modal
    hideModal('deleteNewsModal');

    // Delete the news item using centralized deleteRequest
    try {
        const response = await deleteRequest(`/admin/news/${deleteNewsId}`);
        const data = await response.json();

        if (data.success) {
            window.location.reload();
        } else {
            showToast(`Error deleting news: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showToast(`Error deleting news: ${error.message}`, 'error');
    }
}
