<script setup>
import { ref, nextTick } from 'vue'

const emit = defineEmits(['confirm', 'cancel'])

const input = ref(null)
const userId = ref('')

const handleConfirm = () => {
  if (userId.value.trim()) {
    emit('confirm', userId.value.trim())
    userId.value = ''
  }
}

const handleCancel = () => {
  userId.value = ''
  emit('cancel')
}

const handleKeydown = (e) => {
  if (e.key === 'Enter') {
    handleConfirm()
  } else if (e.key === 'Escape') {
    handleCancel()
  }
}

// Focus input on mount
nextTick(() => {
  input.value?.focus()
})
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click="handleCancel">
      <div class="modal-content" @click.stop>
        <h2 class="modal-title">Create New User</h2>

        <input
          ref="input"
          v-model="userId"
          type="text"
          placeholder="Enter user ID..."
          class="modal-input"
          @keydown="handleKeydown"
        />

        <div class="modal-actions">
          <button class="modal-button cancel" @click="handleCancel">
            Cancel
          </button>
          <button
            class="modal-button confirm"
            :disabled="!userId.trim()"
            @click="handleConfirm"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: var(--spacing-md);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  width: 100%;
  max-width: 360px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.25s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md);
}

.modal-input {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: var(--font-size-base);
  transition: all var(--transition-fast);
  outline: none;
}

.modal-input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.modal-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  justify-content: flex-end;
}

.modal-button {
  padding: 10px 18px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.modal-button.cancel {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.modal-button.cancel:hover {
  background: var(--border-color);
}

.modal-button.confirm {
  background: var(--accent-color);
  color: white;
}

.modal-button.confirm:hover:not(:disabled) {
  background: var(--accent-hover);
}

.modal-button.confirm:disabled {
  background: var(--border-color);
  color: var(--text-muted);
  cursor: not-allowed;
}
</style>
