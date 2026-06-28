<script setup>
import { ref, nextTick, watch } from 'vue'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import MobileHeader from './MobileHeader.vue'

const props = defineProps({
  messages: Array,
  isLoading: Boolean,
  streamingContent: String,
  userId: String
})

const emit = defineEmits(['send-message', 'stop-generation', 'toggle-sidebar'])

const messagesContainer = ref(null)
const showScrollButton = ref(false)

// Scroll to bottom when messages change
watch(() => [props.messages, props.streamingContent], async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

const scrollToBottom = (smooth = true) => {
  if (!messagesContainer.value) return
  const container = messagesContainer.value
  container.scrollTo({
    top: container.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto'
  })
}

const handleScroll = () => {
  if (!messagesContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value
  const distanceFromBottom = scrollHeight - scrollTop - clientHeight
  showScrollButton.value = distanceFromBottom > 200
}

const handleSend = async (content) => {
  await emit('send-message', content)
}
</script>

<template>
  <div class="chat-view">
    <!-- Mobile Header -->
    <MobileHeader
      :user-id="userId"
      @toggle-sidebar="emit('toggle-sidebar')"
    />

    <!-- Messages Container -->
    <div
      ref="messagesContainer"
      class="messages-container"
      @scroll="handleScroll"
    >
      <MessageList
        :messages="messages"
        :is-loading="isLoading"
        :streaming-content="streamingContent"
      />
    </div>

    <!-- Scroll to Bottom Button -->
    <button
      v-if="showScrollButton"
      class="scroll-button"
      @click="scrollToBottom"
      aria-label="Scroll to bottom"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 5v14M19 12l-7 7-7-7"/>
      </svg>
    </button>

    <!-- Input Area -->
    <InputArea
      :disabled="isLoading"
      @send="handleSend"
      @stop="emit('stop-generation')"
    />
  </div>
</template>

<style scoped>
.chat-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  background: var(--bg-primary);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
  scroll-behavior: smooth;
}

.scroll-button {
  position: absolute;
  bottom: 100px;
  right: var(--spacing-md);
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-fast);
  z-index: 10;
}

.scroll-button:hover {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
  transform: translateY(-2px);
}

.scroll-button svg {
  width: 20px;
  height: 20px;
}

@media (max-width: 768px) {
  .messages-container {
    padding: var(--spacing-sm);
  }

  .scroll-button {
    bottom: 90px;
    right: var(--spacing-sm);
    width: 36px;
    height: 36px;
  }
}
</style>
