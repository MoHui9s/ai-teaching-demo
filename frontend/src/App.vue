<script setup>
import { ref, onMounted } from 'vue'
import { useDarkMode } from './composables/useDarkMode'
import { useUsers } from './composables/useUsers'
import { useChat } from './composables/useChat'
import ChatView from './components/ChatView.vue'
import Sidebar from './components/Sidebar.vue'
import UserModal from './components/UserModal.vue'

const { isDark, toggleDark } = useDarkMode()
const { currentUserId, users, switchUser, createNewUser, clearHistory, loadUsers } = useUsers()
const {
  messages,
  isLoading,
  streamingContent,
  sendMessage,
  stopGeneration,
  loadHistory,
  messageCount
} = useChat(currentUserId)

const sidebarOpen = ref(false)
const showUserModal = ref(false)

// Load initial data
onMounted(async () => {
  await loadUsers()
  await loadHistory()
})

// Handle user switch
const handleSwitchUser = async (userId) => {
  await switchUser(userId)
  sidebarOpen.value = false
}

// Handle new user creation
const handleCreateUser = async (userId) => {
  await createNewUser(userId)
  showUserModal.value = false
  sidebarOpen.value = false
}

// Handle clear history
const handleClearHistory = async () => {
  await clearHistory()
}

// Toggle sidebar
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

// Close sidebar when clicking overlay (mobile)
const closeSidebar = () => {
  sidebarOpen.value = false
}
</script>

<template>
  <div :class="['app', { dark: isDark }]">
    <!-- Mobile Overlay -->
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      @click="closeSidebar"
    ></div>

    <!-- Sidebar -->
    <Sidebar
      :open="sidebarOpen"
      :current-user-id="currentUserId"
      :users="users"
      :message-count="messageCount"
      :is-dark="isDark"
      @switch-user="handleSwitchUser"
      @new-user="showUserModal = true"
      @toggle-dark="toggleDark"
      @clear-history="handleClearHistory"
      @close="closeSidebar"
    />

    <!-- Main Chat Area -->
    <ChatView
      :messages="messages"
      :is-loading="isLoading"
      :streaming-content="streamingContent"
      :user-id="currentUserId"
      @send-message="sendMessage"
      @stop-generation="stopGeneration"
      @toggle-sidebar="toggleSidebar"
    />

    <!-- User Modal -->
    <UserModal
      v-if="showUserModal"
      @confirm="handleCreateUser"
      @cancel="showUserModal = false"
    />
  </div>
</template>

<style>
/* Global styles will be in main.css */
.app {
  width: 100%;
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 40;
  opacity: 0;
  animation: fadeIn 0.25s ease forwards;
}

@keyframes fadeIn {
  to { opacity: 1; }
}
</style>
