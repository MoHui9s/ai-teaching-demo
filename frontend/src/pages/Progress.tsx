import { useEffect, useState } from 'react'
import { progress } from '../api/client'
import { Flame, Clock, Mic, BookOpen } from 'lucide-react'

export default function Progress() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    progress.overview().then(res => {
      if (res?.data) setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-5 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/2" />
        <div className="h-40 bg-gray-200 rounded-2xl" />
      </div>
    )
  }

  const stats = [
    { icon: Flame, label: '连续打卡', value: `${data?.streak_days || 0} 天`, color: 'text-orange-500', bg: 'bg-orange-50' },
    { icon: Clock, label: '本周学习', value: `${data?.week_total_minutes || 0} 分钟`, color: 'text-blue-500', bg: 'bg-blue-50' },
    { icon: Mic, label: '本月学习', value: `${data?.month_total_minutes || 0} 分钟`, color: 'text-purple-500', bg: 'bg-purple-50' },
  ]

  return (
    <div className="p-5 space-y-5">
      <h1 className="page-title">学习进度</h1>
      <p className="page-subtitle">追踪你的英语学习足迹</p>

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-3">
        {stats.map((s, i) => (
          <div key={i} className={`card flex flex-col items-center py-4 ${s.bg}`}>
            <s.icon size={20} className={`${s.color} mb-1`} />
            <span className="text-lg font-bold">{s.value}</span>
            <span className="text-xs text-gray-500">{s.label}</span>
          </div>
        ))}
      </div>

      {/* 热力图 */}
      {data?.heatmap_data && (
        <div className="card">
          <h3 className="font-semibold mb-3">学习热力图（近 90 天）</h3>
          <div className="grid grid-cols-7 gap-1">
            {Object.entries(data.heatmap_data).map(([date, minutes]: [string, any]) => {
              const level = minutes > 30 ? 4 : minutes > 20 ? 3 : minutes > 10 ? 2 : minutes > 0 ? 1 : 0
              return (
                <div
                  key={date}
                  className={`aspect-square rounded-sm heatmap-${level}`}
                  title={`${date}: ${minutes} 分钟`}
                />
              )
            })}
          </div>
          <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
            <span>少</span>
            <div className="w-3 h-3 rounded-sm heatmap-0" />
            <div className="w-3 h-3 rounded-sm heatmap-1" />
            <div className="w-3 h-3 rounded-sm heatmap-2" />
            <div className="w-3 h-3 rounded-sm heatmap-3" />
            <div className="w-3 h-3 rounded-sm heatmap-4" />
            <span>多</span>
          </div>
        </div>
      )}

      {/* 最近活动 */}
      {data?.recent_activities?.length > 0 && (
        <div className="card">
          <h3 className="font-semibold mb-3">最近活动</h3>
          <div className="space-y-2">
            {data.recent_activities.map((act: any, i: number) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className="w-2 h-2 rounded-full bg-primary-500" />
                <span className="flex-1">{act.summary}</span>
                <span className="text-xs text-gray-400">{act.date}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
