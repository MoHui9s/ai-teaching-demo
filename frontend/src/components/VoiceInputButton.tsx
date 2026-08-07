import { useRef, useEffect } from 'react'
import { Mic, MicOff, AlertCircle } from 'lucide-react'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'

interface Props {
  onTranscript: (text: string) => void
  language?: string
  disabled?: boolean
  size?: number
  className?: string
}

export default function VoiceInputButton({
  onTranscript,
  disabled = false,
  size = 20,
  className = '',
}: Props) {
  const {
    isRecording,
    transcript,
    error,
    permissionDenied,
    duration,
    startRecording,
    stopRecording,
  } = useVoiceRecorder()

  const callbackRef = useRef(onTranscript)
  callbackRef.current = onTranscript
  const deliveredRef = useRef<string | null>(null)

  // 转写完成时仅回调一次
  useEffect(() => {
    if (transcript && transcript !== deliveredRef.current) {
      deliveredRef.current = transcript
      callbackRef.current(transcript)
    }
  }, [transcript])

  const handleClick = () => {
    if (isRecording) {
      stopRecording()
    } else {
      deliveredRef.current = null
      startRecording()
    }
  }

  // 权限被拒
  if (permissionDenied) {
    return (
      <button
        disabled
        className={`p-2 rounded-full text-gray-300 ${className}`}
        title="麦克风权限未授予，请在浏览器设置中允许"
      >
        <MicOff size={size} />
      </button>
    )
  }

  // 录音中
  if (isRecording) {
    const seconds = duration % 60
    const displayTime = `${String(seconds).padStart(2, '0')}s`

    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-xs text-red-500 font-mono animate-pulse">{displayTime}</span>
        <button
          onClick={handleClick}
          className="p-2 rounded-full bg-red-100 text-red-500 hover:bg-red-200 transition-colors animate-pulse"
          title="停止录音"
        >
          <MicOff size={size} />
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className={`p-2 rounded-full transition-colors text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-50 ${className}`}
      title={error || '语音输入'}
    >
      {error ? <AlertCircle size={size} className="text-amber-500" /> : <Mic size={size} />}
    </button>
  )
}
