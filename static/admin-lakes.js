/**
 * Admin Lakes page JavaScript functionality
 * Handles lake CRUD operations and delete confirmation
 */

// Initialize delete confirmation manager
let lakeDeleteManager;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize delete confirmation manager
    lakeDeleteManager = new DeleteConfirmationManager({
        modalId: 'deleteLakeModal',
        itemNameElementId: 'delete-lake-name',
        confirmInputId: 'delete-confirmation',
        confirmButtonId: 'confirmDeleteLakeBtn',
        deleteUrlTemplate: (id) => `/admin/lakes/${id}`,
        onSuccess: () => location.reload(),
        onError: (error) => showToast(`Error deleting lake: ${error}`, 'error')
    });

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
    lakeDeleteManager.confirm(id, displayName);
}
