import { ref, watch } from 'vue'
import { streamChat } from '../utils/api'

const MAX_MESSAGE_LENGTH = 8000

export function useChat(userId) {
  const messages = ref([])
  const isLoading = ref(false)
  const streamingContent = ref('')
  const messageCount = ref(0)
  const controller = ref(null) // AbortController

  const loadHistory = async () => {
    try {
      const response = await fetch(`/v1/users/${userId.value}/history`)
      if (!response.ok) throw new Error(`Failed to load history (${response.status})`)
      const data = await response.json()
      messages.value = data.messages || []
      messageCount.value = data.count || messages.value.length
    } catch (error) {
      console.error('Failed to load history:', error)
      messages.value = []
      messageCount.value = 0
    }
  }

  // Load history when userId changes
  watch(userId, () => {
    loadHistory()
  }, { immediate: true })

  const sendMessage = async (content) => {
    if (!content?.trim() || isLoading.value) return false

    const trimmedContent = content.trim()
    if (trimmedContent.length > MAX_MESSAGE_LENGTH) {
      throw new Error(`Message too long (${trimmedContent.length}/${MAX_MESSAGE_LENGTH})`)
    }

    // Add user message
    const userMsg = {
      role: 'user',
      content: trimmedContent,
      timestamp: new Date().toISOString()
    }
    messages.value.push(userMsg)

    // Start loading
    isLoading.value = true
    streamingContent.value = ''
    controller.value = new AbortController()

    try {
      // Stream the response
      let assistantContent = ''
      await streamChat(
        [...messages.value],
        userId.value,
        (chunk) => {
          streamingContent.value = chunk
        },
        controller.value.signal
      )

      assistantContent = streamingContent.value

      // Add assistant message
      const assistantMsg = {
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date().toISOString()
      }
      messages.value.push(assistantMsg)
      messageCount.value++
      streamingContent.value = ''
      return true
    } catch (error) {
      if (error.name === 'AbortError') {
        // User stopped the generation
        if (streamingContent.value) {
          const partialMsg = {
            role: 'assistant',
            content: streamingContent.value + '\n\n*[Stopped by user]*',
            timestamp: new Date().toISOString()
          }
          messages.value.push(partialMsg)
        }
      } else {
        // Show error
        const errorMsg = {
          role: 'error',
          content: error.message || 'An error occurred',
          timestamp: new Date().toISOString()
        }
        messages.value.push(errorMsg)
      }
      streamingContent.value = ''
      throw error
    } finally {
      isLoading.value = false
      controller.value = null
    }
  }

  const stopGeneration = () => {
    if (controller.value) {
      controller.value.abort()
      controller.value = null
    }
    isLoading.value = false
  }

  return {
    messages,
    isLoading,
    streamingContent,
    messageCount,
    sendMessage,
    stopGeneration,
    loadHistory
  }
}
