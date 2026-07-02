<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useDarkMode } from '../composables/useDarkMode'
import { useUsers } from '../composables/useUsers'
import { useChat } from '../composables/useChat'
import ChatView from '../components/ChatView.vue'
import Sidebar from '../components/Sidebar.vue'
import UserModal from '../components/UserModal.vue'
import UserManagement from '../components/UserManagement.vue'

const router = useRouter()
const { adminLogout, isAdminLoggedIn } = useAuth()
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
const currentTab = ref('chat') // 'chat' or 'users'

onMounted(async () => {
  if (!isAdminLoggedIn()) {
    router.push('/admin')
    return
  }
  await loadUsers()
  await loadHistory()
})

const handleSwitchUser = async (userId) => {
  await switchUser(userId)
  sidebarOpen.value = false
}

const handleCreateUser = async (userId) => {
  await createNewUser(userId)
  showUserModal.value = false
  sidebarOpen.value = false
}

const handleClearHistory = async () => {
  await clearHistory()
}

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const closeSidebar = () => {
  sidebarOpen.value = false
}

const handleLogout = () => {
  adminLogout()
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
      :is-admin="true"
      @switch-user="handleSwitchUser"
      @new-user="showUserModal = true"
      @toggle-dark="toggleDark"
      @clear-history="handleClearHistory"
      @admin-logout="handleLogout"
      @close="closeSidebar"
    />

    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Tab Navigation -->
      <div class="tab-nav">
        <button
          :class="['tab-btn', { active: currentTab === 'chat' }]"
          @click="currentTab = 'chat'"
        >
          💬 Chat
        </button>
        <button
          :class="['tab-btn', { active: currentTab === 'users' }]"
          @click="currentTab = 'users'"
        >
          👥 Users
        </button>
      </div>

      <!-- Chat Tab -->
      <div v-if="currentTab === 'chat'" class="tab-content">
        <ChatView
          :messages="messages"
          :is-loading="isLoading"
          :streaming-content="streamingContent"
          :user-id="currentUserId"
          @send-message="sendMessage"
          @stop-generation="stopGeneration"
          @toggle-sidebar="toggleSidebar"
        />
      </div>

      <!-- Users Tab -->
      <div v-if="currentTab === 'users'" class="tab-content user-tab">
        <UserManagement />
      </div>
    </div>

    <!-- User Modal (Memory User) -->
    <UserModal
      v-if="showUserModal"
      @confirm="handleCreateUser"
      @cancel="showUserModal = false"
    />
  </div>
</template>

<style>
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

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-nav {
  display: flex;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  padding: 10px 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  background: var(--bg-hover);
}

.tab-btn.active {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}

.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.user-tab {
  overflow-y: auto;
}
</style>
