import { ref, watch } from 'vue'

const API_BASE = ''

const STORAGE_KEY = 'currentUserId'

// Global state
const currentUserId = ref('default')
const users = ref([])

export function useUsers() {
  // Load current user from localStorage
  const storedUser = localStorage.getItem(STORAGE_KEY)
  if (storedUser) {
    currentUserId.value = storedUser
  }

  // Watch for changes and persist
  watch(currentUserId, (value) => {
    localStorage.setItem(STORAGE_KEY, value)
  })

  const loadUsers = async () => {
    try {
      const adminToken = localStorage.getItem('admin_token')
      const headers = {}
      if (adminToken) {
        headers['X-Admin-Token'] = adminToken
      }
      const response = await fetch(`${API_BASE}/v1/users`, { headers })
      if (!response.ok) throw new Error('Failed to fetch users')
      const data = await response.json()
      users.value = data.users || []
    } catch (error) {
      console.error('Failed to load users:', error)
      users.value = []
    }
  }

  const switchUser = async (userId) => {
    if (userId === currentUserId.value) return
    currentUserId.value = userId
  }

  const createNewUser = async (userId) => {
    if (!userId || !userId.trim()) return
    const newId = userId.trim()
    currentUserId.value = newId
    // Reload users list
    await loadUsers()
  }

  const clearHistory = async () => {
    try {
      const adminToken = localStorage.getItem('admin_token')
      const authToken = localStorage.getItem('auth_token')
      const headers = {}
      if (adminToken) {
        headers['X-Admin-Token'] = adminToken
      }
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }
      const response = await fetch(`${API_BASE}/v1/users/${currentUserId.value}/history`, {
        method: 'DELETE',
        headers
      })
      if (!response.ok) throw new Error('Failed to clear history')
      return true
    } catch (error) {
      console.error('Failed to clear history:', error)
      throw error
    }
  }

  return {
    currentUserId,
    users,
    loadUsers,
    switchUser,
    createNewUser,
    clearHistory
  }
}
