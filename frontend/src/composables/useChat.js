import { ref, watch } from 'vue'
import { chatCompletion, fakeStream } from '../utils/api'

const MAX_MESSAGE_LENGTH = 8000
const STREAM_TIMEOUT = 120000 // 120 seconds, matches backend timeout
const CHUNK_SIZE = 3 // Characters per chunk for fake streaming
const CHUNK_DELAY = 20 // Delay between chunks in ms

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

    // Set up timeout to handle stuck requests
    let timeoutId = null
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        controller.value.abort()
        reject(new Error('请求超时了。消息历史可能过长,建议清理部分历史记录或稍后重试。'))
      }, STREAM_TIMEOUT)
    })

    try {
      // Get complete response with timeout
      let assistantContent = ''
      await Promise.race([
        chatCompletion(
          [...messages.value],
          userId.value,
          controller.value.signal
        ).then(async (response) => {
          // Simulate streaming with the complete response
          await fakeStream(
            response,
            (chunk) => {
              streamingContent.value = chunk
            },
            CHUNK_SIZE,
            CHUNK_DELAY
          )
          assistantContent = response
        }),
        timeoutPromise
      ])

      // Clear timeout if request completed successfully
      if (timeoutId) clearTimeout(timeoutId)

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
      // Clear timeout
      if (timeoutId) clearTimeout(timeoutId)

      if (error.name === 'AbortError') {
        // Check if it was aborted by timeout or user
        if (error.message.includes('请求超时')) {
          // Timeout occurred
          const timeoutMsg = {
            role: 'error',
            content: error.message,
            timestamp: new Date().toISOString()
          }
          messages.value.push(timeoutMsg)
        } else if (streamingContent.value) {
          // User stopped the generation
          const partialMsg = {
            role: 'assistant',
            content: streamingContent.value + '\n\n*[Stopped by user]*',
            timestamp: new Date().toISOString()
          }
          messages.value.push(partialMsg)
        }
      } else {
        // Network or other error - show user-friendly message
        const userFriendlyError = error.message.includes('fetch') ||
          error.message.includes('network') ||
          error.message.includes('Network')
          ? '网络连接出现问题,请检查网络后重试。'
          : (error.message || '服务暂时不可用,请稍后重试。')

        const errorMsg = {
          role: 'error',
          content: userFriendlyError,
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
