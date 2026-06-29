<script setup>
import { ref } from 'vue'

const props = defineProps({
  open: Boolean,
  currentUserId: String,
  users: Array,
  messageCount: Number,
  isDark: Boolean
})

const emit = defineEmits([
  'switch-user',
  'new-user',
  'toggle-dark',
  'clear-history',
  'close'
])

const newUserId = ref('')

const handleSwitchUser = (userId) => {
  emit('switch-user', userId)
}

const handleNewUser = () => {
  const id = newUserId.value.trim()
  if (id) {
    emit('new-user', id)
    newUserId.value = ''
  }
}

const handleKeyDown = (e) => {
  if (e.key === 'Enter') {
    handleNewUser()
  }
}

const getUserCount = (userId) => {
  const user = props.users?.find(u => u.user_id === userId)
  return user?.message_count || 0
}

const getUserInitial = (userId) => {
  return userId?.charAt(0)?.toUpperCase() || '?'
}
</script>

<template>
  <aside :class="['sidebar', { open }]">
    <!-- Header -->
    <div class="sidebar-header">
      <div class="sidebar-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        <span>Hermes AI</span>
      </div>
      <button class="close-button" @click="emit('close')" aria-label="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- User Switcher -->
    <div class="user-switcher">
      <label class="field-label">Current User</label>
      <div class="user-input-group">
        <input
          v-model="newUserId"
          type="text"
          placeholder="New user ID..."
          class="user-input"
          @keydown="handleKeyDown"
        />
        <button class="add-button" @click="handleNewUser" :disabled="!newUserId.trim()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- User List -->
    <div class="user-list">
      <div
        v-for="user in users"
        :key="user.user_id"
        :class="['user-item', { active: user.user_id === currentUserId }]"
        @click="handleSwitchUser(user.user_id)"
      >
        <div class="user-avatar">{{ getUserInitial(user.user_id) }}</div>
        <div class="user-info">
          <span class="user-name">{{ user.user_id }}</span>
          <span class="user-count">
            {{ getUserCount(user.user_id) }} message{{ getUserCount(user.user_id) !== 1 ? 's' : '' }}
          </span>
        </div>
        <svg v-if="user.user_id === currentUserId" class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 6L9 17l-5-5"/>
        </svg>
      </div>

      <div v-if="!users || users.length === 0" class="empty-state">
        <p>No users yet. Create one above.</p>
      </div>
    </div>

    <!-- Actions -->
    <div class="sidebar-actions">
      <button class="action-button" @click="emit('clear-history')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
        </svg>
        Clear History
      </button>

      <button class="action-button" @click="emit('toggle-dark')">
        <svg v-if="!isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
        {{ isDark ? 'Light' : 'Dark' }} Mode
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transform: translateX(-100%);
  transition: transform var(--transition-base);
  z-index: 50;
  box-shadow: var(--shadow-lg);
}

.sidebar.open {
  transform: translateX(0);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-weight: 600;
  font-size: 16px;
  color: var(--text-primary);
}

.sidebar-title svg {
  width: 20px;
  height: 20px;
  color: var(--accent-color);
}

.close-button {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.close-button:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.close-button svg {
  width: 20px;
  height: 20px;
}

.user-switcher {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.field-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: var(--spacing-xs);
}

.user-input-group {
  display: flex;
  gap: var(--spacing-xs);
}

.user-input {
  flex: 1;
  padding: 10px 12px;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
  outline: none;
}

.user-input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.add-button {
  width: 40px;
  padding: 0;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--accent-color);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.add-button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.add-button:disabled {
  background: var(--border-color);
  cursor: not-allowed;
  color: var(--text-muted);
}

.add-button svg {
  width: 18px;
  height: 18px;
}

.user-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm) var(--spacing-md);
}

.user-list::-webkit-scrollbar {
  width: 4px;
}

.user-list::-webkit-scrollbar-track {
  background: transparent;
}

.user-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 2px;
}

.user-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 2px;
}

.user-item:hover {
  background: var(--bg-secondary);
}

.user-item.active {
  background: var(--accent-light);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.user-item.active .user-avatar {
  background: var(--accent-color);
  color: white;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-item.active .user-name {
  color: var(--accent-color);
}

.user-count {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.check-icon {
  width: 16px;
  height: 16px;
  color: var(--accent-color);
  flex-shrink: 0;
}

.empty-state {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--font-size-sm);
}

.sidebar-actions {
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.action-button {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-button:hover {
  background: var(--accent-light);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.action-button svg {
  width: 16px;
  height: 16px;
}

@media (min-width: 769px) {
  .sidebar {
    position: sticky;
    transform: translateX(0);
    box-shadow: none;
  }

  .close-button {
    display: none;
  }
}
</style>
