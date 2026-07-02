<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  show: Boolean,
  user: Object
})

const emit = defineEmits(['confirm', 'cancel'])

const email = ref('')
const isActive = ref(true)
const error = ref(null)

// Update form when user changes
watch(() => props.user, (newUser) => {
  if (newUser) {
    email.value = newUser.email || ''
    isActive.value = newUser.is_active !== false
  }
}, { immediate: true })

const handleSubmit = async () => {
  error.value = null

  // Validation
  if (!email.value || !email.value.includes('@')) {
    error.value = 'Please enter a valid email'
    return
  }

  try {
    await emit('confirm', {
      email: email.value,
      is_active: isActive.value
    })
  } catch (e) {
    error.value = e.message
  }
}

const handleCancel = () => {
  emit('cancel')
  error.value = null
}
</script>

<template>
  <div v-if="show && user" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-card">
      <div class="modal-header">
        <h3>Edit User</h3>
        <span class="user-id">{{ user.user_id }}</span>
      </div>
      <div class="modal-body">
        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="user@example.com"
            @keyup.enter="handleSubmit"
          />
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input v-model="isActive" type="checkbox" />
            <span>Active Status</span>
            <span class="status-badge" :class="{ active: isActive, inactive: !isActive }">
              {{ isActive ? 'Active' : 'Inactive' }}
            </span>
          </label>
        </div>

        <div class="info">
          <small>User ID: {{ user.user_id }}</small><br>
          <small>Created: {{ new Date(user.created_at).toLocaleString() }}</small>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="handleCancel" class="btn-cancel">Cancel</button>
        <button @click="handleSubmit" class="btn-confirm">Save Changes</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 450px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-xl);
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-primary);
}

.user-id {
  font-family: monospace;
  font-size: 0.85em;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

.error {
  padding: var(--spacing-sm);
  background: var(--error-bg);
  color: var(--error-color);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-md);
  font-size: 0.9em;
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: 0.9em;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-group input[type="email"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.95em;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.checkbox-label input {
  cursor: pointer;
}

.status-badge {
  margin-left: auto;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 0.85em;
  font-weight: 500;
}

.status-badge.active {
  background: #10b981;
  color: white;
}

.status-badge.inactive {
  background: var(--text-muted);
  color: white;
}

.info {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  line-height: 1.6;
}

.btn-cancel,
.btn-confirm {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 500;
  transition: opacity var(--transition-fast);
}

.btn-cancel {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.btn-cancel:hover {
  opacity: 0.8;
}

.btn-confirm {
  background: var(--accent-color);
  color: white;
}

.btn-confirm:hover {
  opacity: 0.9;
}
</style>
