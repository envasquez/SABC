/**
 * Admin Edit Lake page JavaScript functionality
 * Handles ramp CRUD operations and delete confirmation
 */

// Initialize delete confirmation manager for ramps
let rampDeleteManager;

document.addEventListener('DOMContentLoaded', function() {
    // Edit ramp buttons
    document.querySelectorAll('.edit-ramp-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const name = this.dataset.name;
            const map = this.dataset.map;

            // Set form action
            document.getElementById('editRampForm').action = `/admin/ramps/${id}/update`;

            // Fill form fields
            document.getElementById('edit_ramp_name').value = name;
            document.getElementById('edit_google_maps_iframe').value = map;

            // Show modal
            showModal('editRampModal');
        });
    });

    // Initialize delete confirmation manager for ramps
    rampDeleteManager = new DeleteConfirmationManager({
        modalId: 'deleteRampModal',
        itemNameElementId: 'delete-ramp-name',
        confirmInputId: 'delete-ramp-confirmation',
        confirmButtonId: 'confirmDeleteRampBtn',
        deleteUrlTemplate: (id) => `/admin/ramps/${id}`,
        onSuccess: () => location.reload(),
        onError: (error) => showToast(`Error deleting ramp: ${error}`, 'error')
    });

    // Delete ramp buttons
    document.querySelectorAll('.delete-ramp-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const name = this.dataset.name;
            rampDeleteManager.confirm(id, name);
        });
    });
});
