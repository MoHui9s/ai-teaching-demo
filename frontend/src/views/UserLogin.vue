<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'

const { login, isLoading, error } = useAuth()

const email = ref('')
const password = ref('')
const devMode = ref(false)
const defaultEmail = ref('')

onMounted(async () => {
  try {
    const response = await fetch('/api/auth/dev-check')
    const data = await response.json()
    devMode.value = data.dev_mode
    defaultEmail.value = data.default_email
    if (data.dev_mode) {
      email.value = data.default_email
    }
  } catch (e) {
    console.error('Failed to check dev mode')
  }
})

const handleLogin = async () => {
  if (!email.value || !password.value) {
    error.value = 'Please enter email and password'
    return
  }
  try {
    await login(email.value, password.value)
  } catch (e) {
    // Error is already set in the auth composable
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h1>English Learning Assistant</h1>
      <p class="subtitle">Sign in to start learning</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
            :disabled="isLoading"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="••••••••"
            required
            :disabled="isLoading"
          />
        </div>

        <p v-if="devMode" class="dev-hint">
          Dev mode: Use {{ defaultEmail }} / password
        </p>

        <p v-if="error" class="error">{{ error }}</p>

        <button type="submit" :disabled="isLoading" class="login-btn">
          {{ isLoading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: white;
  padding: 2.5rem;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.75rem;
  color: #1a1a1a;
}

.subtitle {
  margin: 0 0 2rem 0;
  color: #666;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
}

input {
  padding: 0.75rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: #667eea;
}

input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dev-hint {
  font-size: 0.875rem;
  color: #667eea;
  background: #f0f4ff;
  padding: 0.75rem;
  border-radius: 8px;
  margin: 0;
}

.error {
  color: #e53e3e;
  font-size: 0.875rem;
  margin: 0;
}

.login-btn {
  padding: 0.875rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-btn:not(:disabled):hover {
  opacity: 0.9;
}
</style>
