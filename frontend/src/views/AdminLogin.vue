<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { verifyAdmin, isLoading, error, isAdminLoggedIn } = useAuth()

const adminToken = ref('')
const isEnabled = ref(false)

onMounted(async () => {
  // Check if already logged in
  if (isAdminLoggedIn()) {
    router.push('/admin/dashboard')
    return
  }

  // Check if admin is enabled
  try {
    const response = await fetch('/api/admin/status')
    const data = await response.json()
    isEnabled.value = data.enabled
    if (!data.enabled) {
      error.value = 'Admin interface is not enabled'
    }
  } catch (e) {
    error.value = 'Failed to connect to server'
  }
})

const handleLogin = async () => {
  if (!adminToken.value) {
    error.value = 'Please enter admin token'
    return
  }
  try {
    await verifyAdmin(adminToken.value)
  } catch (e) {
    // Error is already set
  }
}
</script>

<template>
  <div class="admin-login-container">
    <div class="login-card">
      <h1>Admin Dashboard</h1>
      <p class="subtitle">Enter admin token to continue</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="token">Admin Token</label>
          <input
            id="token"
            v-model="adminToken"
            type="password"
            placeholder="Enter admin token"
            :disabled="isLoading || !isEnabled"
          />
        </div>

        <div v-if="!isEnabled" class="warning">
          Admin interface is not enabled. Set ADMIN_TOKEN environment variable.
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button
          type="submit"
          :disabled="isLoading || !isEnabled"
          class="login-btn"
        >
          {{ isLoading ? 'Verifying...' : 'Access Dashboard' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.admin-login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.login-card {
  background: white;
  padding: 2.5rem;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
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
}

input:focus {
  outline: none;
  border-color: #1a1a2e;
}

input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.warning {
  background: #fff3cd;
  color: #856404;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
  margin: 0;
}

.error {
  color: #e53e3e;
  font-size: 0.875rem;
  margin: 0;
}

.login-btn {
  padding: 0.875rem;
  background: #1a1a2e;
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
