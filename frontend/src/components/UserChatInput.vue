<script setup>
import { computed } from 'vue'
import InputArea from './InputArea.vue'

const props = defineProps({
  disabled: Boolean,
  messageCount: Number
})

const emit = defineEmits(['send', 'stop', 'clear-history'])

const messageText = computed(() => {
  const count = props.messageCount || 0
  return count === 1 ? '1 message' : `${count} messages`
})
</script>

<template>
  <div class="user-chat-input">
    <!-- Clear History Button Area -->
    <div class="input-header">
      <span class="message-count">{{ messageText }}</span>
      <button
        class="clear-history-btn"
        @click="emit('clear-history')"
        :disabled="disabled"
      >
        Clear History
      </button>
    </div>

    <!-- Input Area -->
    <InputArea
      :disabled="disabled"
      @send="emit('send', $event)"
      @stop="emit('stop')"
    />
  </div>
</template>

<style scoped>
.user-chat-input {
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-color);
}

.input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.message-count {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
}

.clear-history-btn {
  padding: 6px 12px;
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.clear-history-btn:hover:not(:disabled) {
  background: var(--error-bg);
  color: var(--error-color);
  border-color: var(--error-color);
}

.clear-history-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .input-header {
    padding: var(--spacing-xs) var(--spacing-sm);
  }

  .message-count {
    font-size: 11px;
  }

  .clear-history-btn {
    padding: 4px 10px;
    font-size: 11px;
  }
}
</style>
