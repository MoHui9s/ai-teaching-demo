<script setup>
import { computed } from 'vue'
import MessageBubble from './MessageBubble.vue'
import WelcomeScreen from './WelcomeScreen.vue'

const props = defineProps({
  messages: Array,
  isLoading: Boolean,
  streamingContent: String
})

const isEmpty = computed(() => props.messages.length === 0)
const showStreaming = computed(() => props.isLoading || props.streamingContent)

// Combine messages with streaming content for display
const displayMessages = computed(() => {
  if (showStreaming.value && props.streamingContent) {
    return [
      ...props.messages,
      {
        role: 'assistant',
        content: props.streamingContent,
        timestamp: new Date().toISOString(),
        streaming: true
      }
    ]
  }
  return props.messages
})
</script>

<template>
  <div class="message-list">
    <!-- Welcome Screen -->
    <WelcomeScreen v-if="isEmpty" />

    <!-- Messages -->
    <template v-else>
      <MessageBubble
        v-for="(msg, index) in displayMessages"
        :key="`${msg.role}-${index}`"
        :message="msg"
        :is-streaming="msg.streaming"
      />

      <!-- Loading indicator -->
      <div v-if="isLoading && !streamingContent" class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--spacing-sm) var(--spacing-md);
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.32s; }

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
