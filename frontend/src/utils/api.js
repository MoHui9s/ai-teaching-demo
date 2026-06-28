/**
 * Stream chat completion from the API
 * @param {Array} messages - Message history
 * @param {string} userId - User ID
 * @param {Function} onChunk - Callback for each chunk
 * @param {AbortSignal} signal - AbortSignal for cancellation
 * @returns {Promise<string>} - Complete response
 */
export async function streamChat(messages, userId, onChunk, signal) {
  const response = await fetch('/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages,
      user_id: userId,
      stream: true
    }),
    signal
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || `API error: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let accumulatedText = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            onChunk(accumulatedText)
            return accumulatedText
          }

          try {
            const parsed = JSON.parse(data)
            const content = parsed.choices?.[0]?.delta?.content
            if (content) {
              accumulatedText += content
              onChunk(accumulatedText)
            }

            // Check for tool status
            if (parsed.usage?.tool_status) {
              // Could emit a status event
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }

  return accumulatedText
}
