import { Clock } from 'lucide-react'

interface Props {
  minutes: number
}

function formatTime(minutes: number): string {
  if (minutes < 1) return '<1 分钟'
  if (minutes < 60) {
    const m = Math.floor(minutes)
    return `${m} 分钟`
  }
  const h = Math.floor(minutes / 60)
  const m = Math.floor(minutes % 60)
  return m > 0 ? `${h}h ${m}m` : `${h} 小时`
}

export default function StudyTimer({ minutes }: Props) {
  return (
    <div className="flex items-center gap-1 bg-blue-50 text-blue-600 px-3 py-1.5 rounded-full">
      <Clock size={16} />
      <span className="font-bold text-sm">{formatTime(minutes)}</span>
    </div>
  )
}
