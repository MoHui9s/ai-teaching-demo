<script setup>
const props = defineProps({
  userId: String
})

const emit = defineEmits(['toggle-sidebar'])
</script>

<template>
  <header class="mobile-header">
    <button class="menu-button" @click="emit('toggle-sidebar')" aria-label="Open menu">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 12h18M3 6h18M3 18h18"/>
      </svg>
    </button>

    <div class="header-title">
      <span class="app-name">Hermes AI</span>
      <span v-if="userId" class="user-badge">{{ userId }}</span>
    </div>

    <div class="header-spacer"></div>
  </header>
</template>

<style scoped>
.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-elevated);
  flex-shrink: 0;
}

.menu-button {
  width: 40px;
  height: 40px;
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

.menu-button:active {
  background: var(--bg-secondary);
}

.menu-button svg {
  width: 22px;
  height: 22px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.app-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.user-badge {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-color);
  background: var(--accent-light);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.header-spacer {
  width: 40px;
}

@media (min-width: 769px) {
  .mobile-header {
    display: none;
  }
}
</style>
