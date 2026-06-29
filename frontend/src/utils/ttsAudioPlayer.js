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

    // 事件监听
    this.audio.addEventListener('ended', () => {
      this.isPlaying = false
      this.isLoading = false
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
    })
  }

  /**
   * 播放文本语音
   * @param {string} text - 要播放的文本
   * @param {string} voice - 声音类型（可选）
   */
  async play(text, voice = 'en-US-AriaNeural') {
    if (!text || !text.trim()) {
      console.warn('空文本，无法播放')
      return
    }

    text = text.trim()

    // 如果正在播放相同的文本，不做处理
    if (this.currentText === text && this.isPlaying) {
      console.log('正在播放相同文本')
      return
    }

    // 停止当前播放
    this.stop()

    this.currentText = text
    this.isLoading = true

    try {
      // 从后端获取音频URL
      const url = await this.getAudioUrl(text, voice)
      this.currentUrl = url

      // 播放音频
      this.audio.src = url
      this.audio.load()

      await this.audio.play()
      this.isLoading = false

      console.log(`播放TTS: "${text.substring(0, 30)}..."`)
    } catch (error) {
      console.error('TTS播放失败:', error)
      this.isLoading = false
      throw error
    }
  }

  /**
   * 获取音频URL
   * @param {string} text - 文本
   * @param {string} voice - 声音类型
   * @returns {Promise<string>} 音频URL
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
      console.log('TTS缓存命中')
    }

    return data.audio_url
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
