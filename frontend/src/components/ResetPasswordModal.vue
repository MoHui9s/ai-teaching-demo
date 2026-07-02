<script setup>
import { ref } from 'vue'

const props = defineProps({
  show: Boolean,
  user: Object
})

const emit = defineEmits(['confirm', 'cancel'])

const customPassword = ref('')
const autoGenerate = ref(true)
const error = ref(null)

const handleSubmit = async () => {
  error.value = null

  // Validation
  if (!autoGenerate.value && (!customPassword.value || customPassword.value.length < 6)) {
    error.value = 'Password must be at least 6 characters'
    return
  }

  try {
    await emit('confirm', {
      new_password: autoGenerate.value ? null : customPassword.value
    })

    // Reset form on success
    customPassword.value = ''
    autoGenerate.value = true
  } catch (e) {
    error.value = e.message
  }
}

const handleCancel = () => {
  emit('cancel')
  error.value = null
  customPassword.value = ''
  autoGenerate.value = true
}
</script>

<template>
  <div v-if="show && user" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-card">
      <div class="modal-header">
        <h3>Reset Password</h3>
      </div>
      <div class="modal-body">
        <p class="user-info">Reset password for <strong>{{ user.email }}</strong></p>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-group">
          <label class="radio-label">
            <input v-model="autoGenerate" :value="true" type="radio" />
            <span>Auto-generate secure password</span>
          </label>
        </div>

        <div class="form-group">
          <label class="radio-label">
            <input v-model="autoGenerate" :value="false" type="radio" />
            <span>Set custom password</span>
          </label>
        </div>

        <div v-if="!autoGenerate" class="form-group">
          <label for="customPassword">New Password</label>
          <input
            id="customPassword"
            v-model="customPassword"
            type="password"
            placeholder="Enter new password"
            @keyup.enter="handleSubmit"
          />
        </div>

        <div v-if="autoGenerate" class="info">
          A secure 12-character password will be generated automatically.
        </div>
      </div>
      <div class="modal-footer">
        <button @click="handleCancel" class="btn-cancel">Cancel</button>
        <button @click="handleSubmit" class="btn-confirm">Reset Password</button>
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

.user-info {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--text-secondary);
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

.radio-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  padding: var(--spacing-sm) 0;
}

.radio-label input {
  cursor: pointer;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: 0.9em;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-group input[type="password"] {
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

.info {
  padding: var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.9em;
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
