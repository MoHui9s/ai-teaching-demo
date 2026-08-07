import { Volume2, VolumeX, Loader2 } from 'lucide-react'
import { useAudioPlayer } from '../hooks/useAudioPlayer'

interface Props {
  text: string
  voice?: string
  rate?: string
  size?: number
  className?: string
}

export default function AudioPlayButton({ text, voice, rate, size = 18, className = '' }: Props) {
  const { play, stop, isLoading, isPlaying } = useAudioPlayer()

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (isPlaying) {
      stop()
    } else {
      play(text, voice, rate)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className={`p-1.5 rounded-full transition-colors ${
        isPlaying
          ? 'text-primary-500 bg-primary-50'
          : 'text-gray-400 hover:text-primary-500 hover:bg-primary-50'
      } ${className}`}
      title={isPlaying ? '停止' : '播放朗读'}
    >
      {isLoading ? (
        <Loader2 size={size} className="animate-spin" />
      ) : isPlaying ? (
        <VolumeX size={size} />
      ) : (
        <Volume2 size={size} />
      )}
    </button>
  )
}
