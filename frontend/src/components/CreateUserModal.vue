<script setup>
import { ref } from 'vue'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['confirm', 'cancel'])

const email = ref('')
const password = ref('')
const userId = ref('')
const autoGenerateId = ref(true)
const error = ref(null)

const handleSubmit = async () => {
  error.value = null

  // Validation
  if (!email.value || !email.value.includes('@')) {
    error.value = 'Please enter a valid email'
    return
  }

  if (!password.value || password.value.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }

  if (!autoGenerateId.value && (!userId.value || userId.value.trim())) {
    error.value = 'Please enter a user ID'
    return
  }

  try {
    await emit('confirm', {
      email: email.value,
      password: password.value,
      user_id: autoGenerateId.value ? null : userId.value.trim()
    })

    // Reset form on success
    email.value = ''
    password.value = ''
    userId.value = ''
    autoGenerateId.value = true
  } catch (e) {
    error.value = e.message
  }
}

const handleCancel = () => {
  emit('cancel')
  error.value = null
  email.value = ''
  password.value = ''
  userId.value = ''
  autoGenerateId.value = true
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-card">
      <div class="modal-header">
        <h3>Create User</h3>
      </div>
      <div class="modal-body">
        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-group">
          <label for="email">Email *</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="user@example.com"
            @keyup.enter="handleSubmit"
          />
        </div>

        <div class="form-group">
          <label for="password">Password *</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Min 6 characters"
            @keyup.enter="handleSubmit"
          />
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input v-model="autoGenerateId" type="checkbox" />
            Auto-generate User ID
          </label>
        </div>

        <div v-if="!autoGenerateId" class="form-group">
          <label for="userId">User ID</label>
          <input
            id="userId"
            v-model="userId"
            type="text"
            placeholder="Custom user ID"
          />
        </div>
      </div>
      <div class="modal-footer">
        <button @click="handleCancel" class="btn-cancel">Cancel</button>
        <button @click="handleSubmit" class="btn-confirm">Create User</button>
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
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-primary);
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

.form-group input[type="email"],
.form-group input[type="password"],
.form-group input[type="text"] {
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
  gap: var(--spacing-xs);
  cursor: pointer;
}

.checkbox-label input {
  cursor: pointer;
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
