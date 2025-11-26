/**
 * Admin Lakes page JavaScript functionality
 * Handles lake CRUD operations and delete confirmation
 */

let deleteLakeId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Delete button event listeners
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const displayName = this.dataset.displayName;
            deleteLake(id, displayName);
        });
    });

    // Auto-generate database name from display name
    const displayNameInput = document.getElementById('display_name');
    if (displayNameInput) {
        displayNameInput.addEventListener('input', function() {
            const displayName = this.value;
            const dbName = displayName.toLowerCase()
                .replace(/lake\s+/gi, '')  // Remove "Lake " prefix
                .replace(/\s+/g, '_')       // Replace spaces with underscores
                .replace(/[^a-z0-9_]/g, ''); // Remove non-alphanumeric chars except underscores

            document.getElementById('name').value = dbName;
        });
    }
});

function deleteLake(id, displayName) {
    // Set the lake info in the modal
    deleteLakeId = id;
    document.getElementById('delete-lake-name').textContent = displayName;
    document.getElementById('delete-confirmation').value = '';

    // Show the modal
    showModal('deleteLakeModal');
}

async function confirmDeleteLake() {
    const confirmText = document.getElementById('delete-confirmation').value;

    if (confirmText.trim() !== 'DELETE') {
        showToast('Please type DELETE to confirm', 'warning');
        return;
    }

    // Close the modal
    hideModal('deleteLakeModal');

    // Delete the lake using centralized deleteRequest
    try {
        const response = await deleteRequest(`/admin/lakes/${deleteLakeId}`);
        const data = await response.json();

        if (data.success) {
            window.location.reload();
        } else {
            showToast(`Error deleting lake: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showToast(`Error deleting lake: ${error.message}`, 'error');
    }
}
