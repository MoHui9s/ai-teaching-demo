import { ref, watch, onMounted } from 'vue'

const STORAGE_KEY = 'darkMode'

// Global state shared across all instances
const isDark = ref(false)

export function useDarkMode() {
  onMounted(() => {
    // Load from localStorage or system preference
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored !== null) {
      isDark.value = stored === 'true'
    } else {
      // Use system preference
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
  })

  const toggleDark = () => {
    isDark.value = !isDark.value
  }

  // Watch for changes and persist
  watch(isDark, (value) => {
    localStorage.setItem(STORAGE_KEY, String(value))
    // Update document class for global CSS targeting
    if (value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, { immediate: true })

  return {
    isDark,
    toggleDark
  }
}
