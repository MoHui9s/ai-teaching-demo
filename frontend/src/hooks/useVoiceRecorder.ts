import { useState, useRef, useCallback, useEffect } from 'react'
import { asr } from '../api/client'

export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [transcript, setTranscript] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [permissionDenied, setPermissionDenied] = useState(false)
  const [duration, setDuration] = useState(0)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mimeTypeRef = useRef<string>('audio/webm')

  // 清理
  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    mediaRecorderRef.current = null
    chunksRef.current = []
  }, [])

  useEffect(() => {
    return cleanup
  }, [cleanup])

  const startRecording = useCallback(async () => {
    setError(null)
    setTranscript(null)
    setDuration(0)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // 选择支持的 MIME 类型
      const supportedTypes = ['audio/webm', 'audio/ogg', 'audio/mp4']
      for (const t of supportedTypes) {
        if (MediaRecorder.isTypeSupported(t)) {
          mimeTypeRef.current = t
          break
        }
      }

      const recorder = new MediaRecorder(stream, { mimeType: mimeTypeRef.current })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current })
        try {
          const res = await asr.transcribe(blob)
          if (res?.data?.text) {
            setTranscript(res.data.text)
          } else {
            setError('未识别到语音，请重试')
          }
        } catch (err: any) {
          setError(err.message || '语音识别失败')
        }
        cleanup()
        setIsRecording(false)
      }

      recorder.start()
      setIsRecording(true)

      // 计时
      timerRef.current = setInterval(() => {
        setDuration(d => d + 1)
      }, 1000)

    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setPermissionDenied(true)
        setError('请在浏览器设置中允许麦克风权限')
      } else if (err.name === 'NotFoundError') {
        setError('未检测到麦克风设备')
      } else {
        setError(err.message || '录音启动失败')
      }
      cleanup()
    }
  }, [cleanup])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  return {
    isRecording,
    transcript,
    error,
    permissionDenied,
    duration,
    startRecording,
    stopRecording,
  }
}
