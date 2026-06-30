<script setup>
import { computed, ref, watch } from 'vue'
import MessageBubble from './MessageBubble.vue'
import NpcVoiceMessage from './NpcVoiceMessage.vue'
import WelcomeScreen from './WelcomeScreen.vue'

const props = defineProps({
  messages: Array,
  isLoading: Boolean,
  streamingContent: String
})

const isEmpty = computed(() => props.messages.length === 0)
const showStreaming = computed(() => props.isLoading || props.streamingContent)

// Use a fixed timestamp for streaming message to prevent re-renders
const streamingTimestamp = ref('')
const streamingKey = ref('')

// Combine messages with streaming content for display
const displayMessages = computed(() => {
  if (showStreaming.value && props.streamingContent) {
    // Set timestamp only once when streaming starts
    if (!streamingTimestamp.value) {
      streamingTimestamp.value = new Date().toISOString()
      streamingKey.value = `streaming-${Date.now()}`
    }
    return [
      ...props.messages,
      {
        role: 'assistant',
        content: props.streamingContent,
        timestamp: streamingTimestamp.value,
        streaming: true
      }
    ]
  }
  // Reset timestamp when not streaming
  if (!showStreaming.value) {
    streamingTimestamp.value = ''
    streamingKey.value = ''
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
      <template v-for="(msg, index) in displayMessages" :key="msg.streaming ? streamingKey : `${msg.role}-${index}`">
        <!-- NPC Voice Message -->
        <NpcVoiceMessage
          v-if="msg.role === 'npc-voice'"
          :message="msg"
        />
        <!-- Regular Message Bubble -->
        <MessageBubble
          v-else
          :message="msg"
          :is-streaming="msg.streaming"
        />
      </template>

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
