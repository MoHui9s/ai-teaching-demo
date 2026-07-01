/**
 * Fake streaming by simulating chunks from complete response
 * @param {string} text - Complete response text
 * @param {Function} onChunk - Callback for each chunk
 * @param {number} chunkSize - Size of each chunk (default: 3 chars)
 * @param {number} delay - Delay between chunks in ms (default: 30ms)
 * @returns {Promise<string>} - Complete response
 */
export async function fakeStream(text, onChunk, chunkSize = 3, delay = 30) {
  let accumulatedText = ''

  for (let i = 0; i < text.length; i += chunkSize) {
    const chunk = text.slice(i, i + chunkSize)
    accumulatedText += chunk
    onChunk(accumulatedText)

    // Simulate streaming delay
    await new Promise(resolve => setTimeout(resolve, delay))
  }

  return accumulatedText
}

/**
 * Chat completion using non-streaming API
 * @param {Array} messages - Message history
 * @param {string} userId - User ID
 * @param {AbortSignal} signal - AbortSignal for cancellation
 * @returns {Promise<string>} - Complete response
 */
export async function chatCompletion(messages, userId, signal) {
  const response = await fetch('/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages,
      user_id: userId,
      stream: false
    }),
    signal
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || `API error: ${response.status}`)
  }

  const data = await response.json()
  return data.choices?.[0]?.message?.content || ''
}

/**
 * Request TTS audio
 * @param {string} text - Text to synthesize
 * @param {string} voice - Voice type (default: 'en-US-AriaNeural')
 * @returns {Promise<{audio_url: string, cached: boolean, duration: number, voice: string}>}
 */
export async function requestTTSAudio(text, voice = 'en-US-AriaNeural') {
  const response = await fetch('/api/tts/audio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || `TTS request failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Get available TTS voices
 * @returns {Promise<{voices: object}>}
 */
export async function getTTSVoices() {
  const response = await fetch('/api/tts/voices')

  if (!response.ok) {
    throw new Error(`Failed to get voices: ${response.status}`)
  }

  return response.json()
}

/**
 * Get TTS cache statistics
 * @returns {Promise<object>}
 */
export async function getTTSCacheStats() {
  const response = await fetch('/api/tts/stats')

  if (!response.ok) {
    throw new Error(`Failed to get cache stats: ${response.status}`)
  }

  return response.json()
}

/**
 * Clear TTS cache
 * @returns {Promise<{status: string, message: string}>}
 */
export async function clearTTSCache() {
  const response = await fetch('/api/tts/cache', {
    method: 'DELETE'
  })

  if (!response.ok) {
    throw new Error(`Failed to clear cache: ${response.status}`)
  }

  return response.json()
}
