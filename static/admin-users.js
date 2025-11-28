/**
 * Admin Users page JavaScript functionality
 * Handles user CRUD operations, add modal, and delete confirmation
 */

/**
 * Show the Add User modal
 */
function showAddUserModal() {
    // Clear the form
    document.getElementById('addUserForm').reset();
    // Show the modal
    showModal('addUserModal');
}

/**
 * Submit the add user form
 */
async function submitAddUser() {
    const name = document.getElementById('addUserName').value.trim();
    const email = document.getElementById('addUserEmail').value.trim();
    const phone = document.getElementById('addUserPhone').value.trim();
    const isMember = document.getElementById('userTypeMember').checked;

    // Validate name is required
    if (!name) {
        showToast('Name is required', 'warning');
        return;
    }

    try {
        const response = await fetch('/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-csrf-token': getCsrfToken(),
            },
            body: JSON.stringify({
                name: name,
                email: email || null,
                phone: phone || null,
                member: isMember
            })
        });

        const data = await response.json();

        if (data.success) {
            // Close modal
            hideModal('addUserModal');
            // Show success message and reload
            showToast(data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast('Error: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error creating user:', error);
        showToast('Error creating user: ' + error.message, 'error');
    }
}

// Initialize delete confirmation manager when DOM is ready
let userDeleteManager;

document.addEventListener('DOMContentLoaded', function() {
    userDeleteManager = new DeleteConfirmationManager({
        modalId: 'deleteUserModal',
        itemNameElementId: 'deleteUserName',
        confirmInputId: 'deleteConfirmInput',
        confirmButtonId: 'confirmDeleteBtn',
        deleteUrlTemplate: (id) => `/admin/users/${id}`,
        onSuccess: () => location.reload(),
        onError: (error) => showToast(`Error deleting user: ${error}`, 'error')
    });
});

function deleteUser(userId, userName) {
    userDeleteManager.confirm(userId, userName);
}
