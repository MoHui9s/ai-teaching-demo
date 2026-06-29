/**
 * TTS音频播放器
 * 管理语音合成音频的播放
 */

/**
 * TTS播放器类
 */
class TTSPlayer {
  constructor() {
    this.audio = new Audio()
    this.currentUrl = null
    this.currentText = null
    this.isPlaying = false
    this.isLoading = false
    this.isBusy = false // 播放中或加载中标记

    // 前端音频缓存：Map<text, {url, duration, voice}>
    this.audioCache = new Map()

    // 事件监听
    this.audio.addEventListener('ended', () => {
      this.isPlaying = false
      this.isLoading = false
      this.isBusy = false
    })

    this.audio.addEventListener('play', () => {
      this.isPlaying = true
    })

    this.audio.addEventListener('pause', () => {
      this.isPlaying = false
    })

    this.audio.addEventListener('error', (e) => {
      console.error('TTS音频播放错误:', e)
      this.isLoading = false
      this.isPlaying = false
      this.isBusy = false
    })
  }

  /**
   * 播放文本语音
   * @param {string} text - 要播放的文本
   * @param {string} voice - 声音类型（可选）
   * @returns {Promise<{url: string, cached: boolean, duration: number}>}
   */
  async play(text, voice = 'en-US-AriaNeural') {
    if (!text || !text.trim()) {
      console.warn('空文本，无法播放')
      return { url: null, cached: false, duration: 0 }
    }

    text = text.trim()

    // 如果正在忙碌中，忽略新的播放请求
    if (this.isBusy) {
      console.log('TTS正在播放中，忽略新请求')
      return { url: this.currentUrl, cached: true, duration: 0 }
    }

    // 检查前端缓存
    const cacheKey = `${text}|${voice}`
    const cached = this.audioCache.get(cacheKey)

    if (cached) {
      console.log(`TTS前端缓存命中: "${text.substring(0, 20)}..."`)

      // 先设置忙碌状态，防止stop()重置
      const wasPlaying = this.isPlaying
      this.isBusy = true
      this.isLoading = false

      // 停止当前播放（但保持isBusy状态）
      if (this.isPlaying) {
        this.audio.pause()
        this.audio.currentTime = 0
        this.isPlaying = false
      }

      this.currentText = text
      this.currentUrl = cached.url

      // 播放缓存的音频
      this.audio.src = cached.url
      await this.audio.play()
      this.isPlaying = true

      return { url: cached.url, cached: true, duration: cached.duration }
    }

    // 没有缓存，需要请求
    // 先设置忙碌状态
    this.isBusy = true
    this.isLoading = true

    // 停止当前播放（但保持isBusy状态）
    if (this.isPlaying) {
      this.audio.pause()
      this.audio.currentTime = 0
      this.isPlaying = false
    }

    this.currentText = text

    try {
      // 从后端获取音频URL
      const { url, duration } = await this.getAudioUrl(text, voice)
      this.currentUrl = url

      // 存入前端缓存
      this.audioCache.set(cacheKey, { url, duration, voice })

      // 播放音频
      this.audio.src = url
      this.audio.load()

      await this.audio.play()
      this.isLoading = false

      console.log(`播放TTS: "${text.substring(0, 30)}..."`)

      return { url, cached: false, duration }
    } catch (error) {
      console.error('TTS播放失败:', error)
      this.isLoading = false
      this.isBusy = false
      throw error
    }
  }

  /**
   * 获取音频URL
   * @param {string} text - 文本
   * @param {string} voice - 声音类型
   * @returns {Promise<{url: string, cached: boolean, duration: number}>} 音频信息
   */
  async getAudioUrl(text, voice) {
    const response = await fetch('/api/tts/audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice })
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`TTS请求失败: ${error}`)
    }

    const data = await response.json()

    // 如果是缓存命中，记录
    if (data.cached) {
      console.log('TTS后端缓存命中')
    }

    return {
      url: data.audio_url,
      cached: data.cached,
      duration: data.duration
    }
  }

  /**
   * 停止播放
   */
  stop() {
    if (this.isPlaying) {
      this.audio.pause()
      this.audio.currentTime = 0
      this.isPlaying = false
    }
    this.isLoading = false
    this.isBusy = false
  }

  /**
   * 清除前端缓存
   */
  clearCache() {
    this.audioCache.clear()
    console.log('TTS前端缓存已清除')
  }

  /**
   * 获取缓存大小
   */
  getCacheSize() {
    return this.audioCache.size
  }

  /**
   * 暂停播放
   */
  pause() {
    if (this.isPlaying) {
      this.audio.pause()
    }
  }

  /**
   * 恢复播放
   */
  resume() {
    if (!this.isPlaying && this.audio.src) {
      this.audio.play()
    }
  }

  /**
   * 设置音量
   * @param {number} volume - 音量 (0-1)
   */
  setVolume(volume) {
    this.audio.volume = Math.max(0, Math.min(1, volume))
  }

  /**
   * 设置播放速度
   * @param {number} rate - 速度 (0.5-2)
   */
  setPlaybackRate(rate) {
    this.audio.playbackRate = Math.max(0.5, Math.min(2, rate))
  }

  /**
   * 销毁播放器
   */
  destroy() {
    this.stop()
    this.audio.removeEventListener('ended', null)
    this.audio.removeEventListener('play', null)
    this.audio.removeEventListener('pause', null)
    this.audio.removeEventListener('error', null)
  }
}

// 全局播放器实例
let playerInstance = null

/**
 * 获取全局TTS播放器实例
 * @returns {TTSPlayer}
 */
export function getTTSPlayer() {
  if (!playerInstance) {
    playerInstance = new TTSPlayer()
  }
  return playerInstance
}

/**
 * 快捷函数：播放文本
 * @param {string} text - 要播放的文本
 * @param {string} voice - 声音类型
 */
export async function playTTS(text, voice) {
  const player = getTTSPlayer()
  await player.play(text, voice)
}

/**
 * 快捷函数：停止播放
 */
export function stopTTS() {
  const player = getTTSPlayer()
  player.stop()
}

/**
 * 快捷函数：暂停播放
 */
export function pauseTTS() {
  const player = getTTSPlayer()
  player.pause()
}

/**
 * 快捷函数：恢复播放
 */
export function resumeTTS() {
  const player = getTTSPlayer()
  player.resume()
}

export { TTSPlayer }
