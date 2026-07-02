import { ref } from 'vue'
import { useRouter } from 'vue-router'

const API_BASE = '/api/auth'

export function useAuth() {
  const router = useRouter()
  const isLoading = ref(false)
  const error = ref(null)

  // User login
  const login = async (email, password) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Login failed')
      }

      const data = await response.json()
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('user_id', data.user_id)
      localStorage.setItem('user_email', data.email)

      router.push(`/user/${data.user_id}`)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Admin verification
  const verifyAdmin = async (adminToken) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch('/api/admin/verify', {
        method: 'GET',
        headers: { 'X-Admin-Token': adminToken }
      })

      if (!response.ok) {
        throw new Error('Invalid admin token')
      }

      localStorage.setItem('admin_token', adminToken)
      router.push('/admin/dashboard')
      return true
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // User logout
  const logout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('user_email')
    router.push('/user')
  }

  // Admin logout
  const adminLogout = () => {
    localStorage.removeItem('admin_token')
    router.push('/admin')
  }

  // Check if logged in
  const isLoggedIn = () => {
    return !!localStorage.getItem('auth_token')
  }

  const isAdminLoggedIn = () => {
    return !!localStorage.getItem('admin_token')
  }

  // Get auth header
  const getAuthHeader = () => {
    const token = localStorage.getItem('auth_token')
    return token ? `Bearer ${token}` : null
  }

  return {
    isLoading,
    error,
    login,
    verifyAdmin,
    logout,
    adminLogout,
    isLoggedIn,
    isAdminLoggedIn,
    getAuthHeader
  }
}
