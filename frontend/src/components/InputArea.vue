<script setup>
import { ref, nextRef, computed } from 'vue'

const props = defineProps({
  disabled: Boolean
})

const emit = defineEmits(['send', 'stop'])

const textarea = ref(null)
const content = ref('')
const isComposing = ref(false)

const MAX_LENGTH = 8000
const charCount = computed(() => content.value.length)
const showWarning = computed(() => charCount.value > MAX_LENGTH * 0.9)

const canSend = computed(() => {
  return content.value.trim().length > 0 && charCount.value <= MAX_LENGTH && !props.disabled
})

const focus = () => {
  textarea.value?.focus()
}

const resize = () => {
  if (!textarea.value) return
  textarea.value.style.height = 'auto'
  const newHeight = Math.min(textarea.value.scrollHeight, 180)
  textarea.value.style.height = newHeight + 'px'
}

const handleInput = () => {
  resize()
}

const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !isComposing.value) {
    e.preventDefault()
    handleSend()
  }
}

const handleCompositionStart = () => {
  isComposing.value = true
}

const handleCompositionEnd = () => {
  isComposing.value = false
}

const handleSend = async () => {
  if (!canSend.value) return

  const message = content.value.trim()
  content.value = ''
  resize()

  emit('send', message)
}

defineExpose({
  focus
})
</script>

<template>
  <div class="input-area">
    <div class="input-wrapper">
      <textarea
        ref="textarea"
        v-model="content"
        class="message-input"
        rows="1"
        :disabled="disabled"
        :placeholder="disabled ? 'AI is thinking...' : 'Type a message... (Enter to send, Shift+Enter for new line)'"
        @input="handleInput"
        @keydown="handleKeyDown"
        @compositionstart="handleCompositionStart"
        @compositionend="handleCompositionEnd"
      ></textarea>

      <div class="input-actions">
        <span :class="['char-count', { warning: showWarning }]">
          {{ charCount > 0 ? `${charCount} / ${MAX_LENGTH}` : '' }}
        </span>

        <button
          v-if="disabled"
          class="stop-button"
          @click="emit('stop')"
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12"/>
          </svg>
          Stop
        </button>

        <button
          v-else
          class="send-button"
          :disabled="!canSend"
          @click="handleSend"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
          </svg>
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.input-area {
  border-top: 1px solid var(--border-color);
  padding: var(--spacing-md) var(--spacing-md) var(--spacing-md);
  background: var(--bg-elevated);
}

.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.message-input {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-md);
  resize: none;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: inherit;
  font-size: var(--font-size-base);
  line-height: 1.5;
  transition: all var(--transition-fast);
  outline: none;
  min-height: 44px;
  max-height: 180px;
}

.message-input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.message-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message-input::placeholder {
  color: var(--text-muted);
}

.input-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.char-count {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: auto;
}

.char-count.warning {
  color: var(--warning-color);
}

.send-button,
.stop-button {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: 10px 18px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.send-button {
  background: var(--accent-color);
  color: white;
  box-shadow: var(--shadow-sm);
}

.send-button:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.send-button:active:not(:disabled) {
  transform: translateY(0) scale(0.97);
}

.send-button:disabled {
  background: var(--border-color);
  color: var(--text-muted);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.send-button svg {
  width: 18px;
  height: 18px;
}

.stop-button {
  background: var(--error-color);
  color: white;
  box-shadow: var(--shadow-sm);
}

.stop-button:hover {
  background: #dc2626;
  box-shadow: var(--shadow-md);
}

.stop-button svg {
  width: 14px;
  height: 14px;
}

@media (max-width: 480px) {
  .input-area {
    padding: var(--spacing-sm);
  }

  .message-input {
    padding: 10px 12px;
    font-size: var(--font-size-sm);
    min-height: 40px;
  }

  .send-button,
  .stop-button {
    padding: 8px 14px;
    font-size: var(--font-size-sm);
  }

  .send-button span,
  .stop-button span {
    display: none;
  }

  .send-button svg,
  .stop-button svg {
    width: 20px;
    height: 20px;
  }
}
</style>
