import { useState, useRef, useCallback } from 'react'
import { tts } from '../api/client'

const API_BASE = import.meta.env.VITE_API_BASE || ''

function getStoredVoice(): string {
  return localStorage.getItem('tts_voice') || 'en-US-AriaNeural'
}

export function useAudioPlayer() {
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [voice, setVoiceState] = useState(getStoredVoice)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const setVoice = useCallback((v: string) => {
    localStorage.setItem('tts_voice', v)
    setVoiceState(v)
  }, [])

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    setIsPlaying(false)
    setIsLoading(false)
  }, [])

  const play = useCallback(async (text: string, voiceParam?: string, rate?: string) => {
    // 如果正在播放，先停止
    if (audioRef.current) {
      stop()
    }

    setIsLoading(true)
    setError(null)

    try {
      const v = voiceParam || voice
      const res = await tts.getAudio(text, v, rate || '+0%')
      const audioUrl = API_BASE + res.audio_url

      const audio = new Audio(audioUrl)
      audioRef.current = audio

      audio.onplay = () => {
        setIsLoading(false)
        setIsPlaying(true)
      }

      audio.onended = () => {
        setIsPlaying(false)
        audioRef.current = null
      }

      audio.onerror = () => {
        setError('音频播放失败')
        setIsLoading(false)
        setIsPlaying(false)
        audioRef.current = null
      }

      await audio.play()
    } catch (err: any) {
      setError(err.message || 'TTS 请求失败')
      setIsLoading(false)
    }
  }, [stop, voice])

  return { play, stop, isLoading, isPlaying, error, voice, setVoice }
}
