<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useChat } from '../composables/useChat'
import MessageList from '../components/MessageList.vue'
import UserChatInput from '../components/UserChatInput.vue'
import ConfirmModal from '../components/ConfirmModal.vue'

const router = useRouter()
const route = useRoute()
const { logout, isLoggedIn, getAuthHeader } = useAuth()

// Get user_id from route params
const userId = computed(() => route.params.user_id || localStorage.getItem('user_id'))

// Use chat composable
const {
  messages,
  isLoading,
  streamingContent,
  messageCount,
  sendMessage,
  stopGeneration,
  loadHistory
} = useChat(userId)

const messagesContainer = ref(null)
const showScrollButton = ref(false)
const showClearConfirm = ref(false)

// Check authentication on mount
onMounted(async () => {
  if (!isLoggedIn()) {
    router.push('/user')
    return
  }
  // Load history will be triggered automatically by useChat's watch on userId
})

// Scroll to bottom when messages change
watch(() => [messages.value, streamingContent.value], async () => {
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
  await sendMessage(content)
}

const handleClearHistory = () => {
  showClearConfirm.value = true
}

const confirmClearHistory = async () => {
  showClearConfirm.value = false

  try {
    const headers = {}
    const token = localStorage.getItem('auth_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`/v1/users/${userId.value}/history`, {
      method: 'DELETE',
      headers
    })

    if (response.ok) {
      messages.value = []
      messageCount.value = 0
    } else {
      throw new Error('Failed to clear history')
    }
  } catch (e) {
    console.error('Failed to clear history:', e)
    alert('Failed to clear history. Please try again.')
  }
}

const handleLogout = () => {
  logout()
}
</script>

<template>
  <div class="user-chat-view">
    <!-- Header -->
    <header class="chat-header">
      <div class="header-left">
        <h1 class="header-title">{{ userId }}</h1>
      </div>
      <div class="header-right">
        <button @click="handleLogout" class="logout-btn" title="Logout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
          </svg>
          Logout
        </button>
      </div>
    </header>

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

    <!-- Input Area with Clear History -->
    <UserChatInput
      :disabled="isLoading"
      :message-count="messageCount"
      @send="handleSend"
      @stop="stopGeneration"
      @clear-history="handleClearHistory"
    />

    <!-- Clear History Confirmation Modal -->
    <ConfirmModal
      :show="showClearConfirm"
      title="Clear History"
      message="Clear all conversation history? This cannot be undone."
      confirm-text="Clear"
      cancel-text="Cancel"
      :dangerous="true"
      @confirm="confirmClearHistory"
      @cancel="showClearConfirm = false"
    />
  </div>
</template>

<style scoped>
.user-chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color);
  height: 60px;
  flex-shrink: 0;
}

.header-left {
  flex: 1;
}

.header-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  gap: var(--spacing-sm);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: 8px 16px;
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  background: var(--error-bg);
  color: var(--error-color);
  border-color: var(--error-color);
}

.logout-btn svg {
  width: 18px;
  height: 18px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
  scroll-behavior: smooth;
}

.scroll-button {
  position: absolute;
  bottom: 120px;
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
  .chat-header {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .header-title {
    font-size: 1.1rem;
  }

  .logout-btn span {
    display: none;
  }

  .messages-container {
    padding: var(--spacing-sm);
  }

  .scroll-button {
    bottom: 110px;
    right: var(--spacing-sm);
    width: 36px;
    height: 36px;
  }
}
</style>
