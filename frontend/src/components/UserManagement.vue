<script setup>
import { ref, onMounted } from 'vue'
import CreateUserModal from './CreateUserModal.vue'
import EditUserModal from './EditUserModal.vue'
import ResetPasswordModal from './ResetPasswordModal.vue'
import ConfirmModal from './ConfirmModal.vue'

const users = ref([])
const loading = ref(false)
const error = ref(null)

// Modal states
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showResetModal = ref(false)
const showDeleteConfirm = ref(false)

// Reset password result
const showPasswordResult = ref(false)
const newPasswordResult = ref('')

// Selected user for actions
const selectedUser = ref(null)

// Fetch users
const fetchUsers = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await fetch('/api/admin/users', {
      headers: { 'X-Admin-Token': localStorage.getItem('admin_token') }
    })

    if (!response.ok) throw new Error('Failed to fetch users')

    const data = await response.json()
    users.value = data.users
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// Create user
const handleCreateUser = async (userData) => {
  try {
    const response = await fetch('/api/admin/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': localStorage.getItem('admin_token')
      },
      body: JSON.stringify(userData)
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to create user')
    }

    showCreateModal.value = false
    await fetchUsers()
  } catch (e) {
    throw e
  }
}

// Edit user
const handleEditUser = async (userData) => {
  try {
    const response = await fetch(`/api/admin/users/${selectedUser.value.user_id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': localStorage.getItem('admin_token')
      },
      body: JSON.stringify(userData)
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to update user')
    }

    showEditModal.value = false
    await fetchUsers()
  } catch (e) {
    throw e
  }
}

// Delete user
const confirmDeleteUser = async () => {
  try {
    const response = await fetch(`/api/admin/users/${selectedUser.value.user_id}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Token': localStorage.getItem('admin_token') }
    })

    if (!response.ok) throw new Error('Failed to delete user')

    showDeleteConfirm.value = false
    await fetchUsers()
  } catch (e) {
    error.value = e.message
  }
}

// Reset password
const handleResetPassword = async (passwordData) => {
  try {
    const response = await fetch(`/api/admin/users/${selectedUser.value.user_id}/password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': localStorage.getItem('admin_token')
      },
      body: JSON.stringify(passwordData)
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to reset password')
    }

    showResetModal.value = false
    const data = await response.json()

    // Show new password if generated
    if (data.new_password) {
      newPasswordResult.value = data.new_password
      showPasswordResult.value = true
    }
  } catch (e) {
    throw e
  }
}

// Open modals
const openCreateModal = () => {
  showCreateModal.value = true
}

const openEditModal = (user) => {
  selectedUser.value = user
  showEditModal.value = true
}

const openResetModal = (user) => {
  selectedUser.value = user
  showResetModal.value = true
}

const openDeleteConfirm = (user) => {
  selectedUser.value = user
  showDeleteConfirm.value = true
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="user-management">
    <div class="header">
      <h2>User Management</h2>
      <button @click="openCreateModal" class="btn-primary">
        + Create User
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="loading" class="loading">Loading users...</div>

    <div v-else class="user-list">
      <table class="user-table">
        <thead>
          <tr>
            <th>User ID</th>
            <th>Email</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.user_id">
            <td class="user-id">{{ user.user_id }}</td>
            <td class="email">{{ user.email }}</td>
            <td class="status">
              <span :class="{ active: user.is_active, inactive: !user.is_active }">
                {{ user.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="created">{{ new Date(user.created_at).toLocaleDateString() }}</td>
            <td class="actions">
              <button @click="openEditModal(user)" class="btn-small" title="Edit">
                ✏️
              </button>
              <button @click="openResetModal(user)" class="btn-small" title="Reset Password">
                🔑
              </button>
              <button
                @click="openDeleteConfirm(user)"
                class="btn-small btn-danger"
                title="Delete"
                :disabled="user.user_id === 'dev_user'"
              >
                🗑️
              </button>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="5" class="empty">No users found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create User Modal -->
    <CreateUserModal
      :show="showCreateModal"
      @confirm="handleCreateUser"
      @cancel="showCreateModal = false"
    />

    <!-- Edit User Modal -->
    <EditUserModal
      :show="showEditModal"
      :user="selectedUser"
      @confirm="handleEditUser"
      @cancel="showEditModal = false"
    />

    <!-- Reset Password Modal -->
    <ResetPasswordModal
      :show="showResetModal"
      :user="selectedUser"
      @confirm="handleResetPassword"
      @cancel="showResetModal = false"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmModal
      :show="showDeleteConfirm"
      title="Delete User"
      :message="`Are you sure you want to delete user ${selectedUser?.email}? This action cannot be undone.`"
      confirm-text="Delete"
      cancel-text="Cancel"
      :dangerous="true"
      @confirm="confirmDeleteUser"
      @cancel="showDeleteConfirm = false"
    />

    <!-- Password Reset Result Modal -->
    <ConfirmModal
      :show="showPasswordResult"
      title="Password Reset"
      :message="`Password has been reset successfully. New password: ${newPasswordResult}`"
      confirm-text="OK"
      cancel-text=""
      :dangerous="false"
      @confirm="showPasswordResult = false"
      @cancel="showPasswordResult = false"
    />
  </div>
</template>

<style scoped>
.user-management {
  padding: var(--spacing-lg);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.btn-primary {
  padding: 10px 20px;
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 500;
  transition: opacity var(--transition-fast);
}

.btn-primary:hover {
  opacity: 0.9;
}

.error {
  padding: var(--spacing-md);
  background: var(--error-bg);
  color: var(--error-color);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-md);
}

.loading {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--text-muted);
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.user-table th,
.user-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.user-table th {
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-secondary);
}

.user-table tr:last-child td {
  border-bottom: none;
}

.user-table tbody tr:hover {
  background: var(--bg-hover);
}

.user-id {
  font-family: monospace;
  font-size: 0.9em;
  color: var(--text-muted);
}

.status .active {
  color: #10b981;
  font-weight: 500;
}

.status .inactive {
  color: var(--text-muted);
}

.actions {
  display: flex;
  gap: var(--spacing-xs);
}

.btn-small {
  padding: 6px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 1rem;
  transition: all var(--transition-fast);
}

.btn-small:hover:not(:disabled) {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger:hover:not(:disabled) {
  background: var(--error-color);
  border-color: var(--error-color);
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: var(--spacing-xl);
}

@media (max-width: 768px) {
  .user-table {
    font-size: 0.9em;
  }

  .user-table th,
  .user-table td {
    padding: 10px 12px;
  }

  .header {
    flex-direction: column;
    gap: var(--spacing-md);
    align-items: stretch;
  }
}
</style>
