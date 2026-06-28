<script setup>
// Simple welcome component - no logic needed
</script>

<template>
  <div class="welcome-screen">
    <div class="welcome-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
      </svg>
    </div>

    <h1 class="welcome-title">Hermes AI</h1>
    <p class="welcome-subtitle">Your Personal AI Assistant</p>

    <p class="welcome-description">
      Start a conversation below. Hermes remembers your context and can perform complex tasks with persistent memory.
    </p>

    <div class="features">
      <div class="feature">
        <span class="feature-icon">🧠</span>
        <span>Persistent Memory</span>
      </div>
      <div class="feature">
        <span class="feature-icon">👥</span>
        <span>Multi-User</span>
      </div>
      <div class="feature">
        <span class="feature-icon">📝</span>
        <span>Markdown</span>
      </div>
      <div class="feature">
        <span class="feature-icon">💻</span>
        <span>Code Support</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.welcome-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--spacing-xl);
  gap: var(--spacing-md);
}

.welcome-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--accent-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-color);
}

.welcome-icon svg {
  width: 32px;
  height: 32px;
}

.welcome-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.welcome-subtitle {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-secondary);
  margin: 0;
}

.welcome-description {
  font-size: var(--font-size-base);
  color: var(--text-muted);
  max-width: 360px;
  line-height: 1.6;
  margin: 0;
}

.features {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  justify-content: center;
  margin-top: var(--spacing-sm);
}

.feature {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-full);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.feature-icon {
  font-size: 16px;
}

@media (max-width: 480px) {
  .welcome-screen {
    padding: var(--spacing-md);
  }

  .welcome-icon {
    width: 56px;
    height: 56px;
  }

  .welcome-icon svg {
    width: 28px;
    height: 28px;
  }

  .welcome-title {
    font-size: 20px;
  }

  .welcome-subtitle {
    font-size: 14px;
  }

  .welcome-description {
    font-size: var(--font-size-sm);
    max-width: 280px;
  }

  .features {
    gap: var(--spacing-xs);
  }

  .feature {
    padding: 6px 12px;
    font-size: 12px;
  }
}
</style>
