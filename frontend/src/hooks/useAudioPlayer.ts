import { useState, useRef, useCallback } from 'react'
import { tts } from '../api/client'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export function useAudioPlayer() {
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    setIsPlaying(false)
    setIsLoading(false)
  }, [])

  const play = useCallback(async (text: string, voice?: string, rate?: string) => {
    // 如果正在播放，先停止
    if (audioRef.current) {
      stop()
    }

    setIsLoading(true)
    setError(null)

    try {
      const res = await tts.getAudio(text, voice || 'en-US-AriaNeural', rate || '+0%')
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
  }, [stop])

  return { play, stop, isLoading, isPlaying, error }
}
