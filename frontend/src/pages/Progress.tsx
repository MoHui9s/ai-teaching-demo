import { useEffect, useState } from 'react'
import { progress } from '../api/client'
import { Flame, Clock, Mic, BookOpen, Star, AlertTriangle, Calendar, MessageCircle } from 'lucide-react'

export default function Progress() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'overview' | 'weekly'>('overview')
  const [weeklyData, setWeeklyData] = useState<any>(null)

  useEffect(() => {
    progress.overview().then(res => {
      if (res?.data) setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (tab === 'weekly' && !weeklyData) {
      progress.weeklyReport().then(res => {
        if (res?.data) setWeeklyData(res.data)
      }).catch(() => {})
    }
  }, [tab]) // eslint-disable-line react-hooks/exhaustive-deps

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

      {/* Tab 切换 */}
      <div className="flex bg-gray-100 rounded-xl p-1">
        <button
          onClick={() => setTab('overview')}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === 'overview' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
          }`}
        >
          概览
        </button>
        <button
          onClick={() => setTab('weekly')}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === 'weekly' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
          }`}
        >
          周报
        </button>
      </div>

      {tab === 'overview' && (
      <>
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
      </>
      )}

      {tab === 'weekly' && (
      <>
        {weeklyData ? (
          <>
            {/* 周报日期 */}
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Calendar size={14} />
              <span>{weeklyData.week_start} ~ {weeklyData.week_end}</span>
            </div>

            {/* 统计卡片 */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { icon: Clock, label: '学习时长', value: `${weeklyData.stats?.total_minutes || 0} 分钟`, color: 'text-blue-500', bg: 'bg-blue-50' },
                { icon: BookOpen, label: '完成任务', value: `${weeklyData.stats?.total_tasks || 0} 个`, color: 'text-green-500', bg: 'bg-green-50' },
                { icon: Flame, label: '学习天数', value: `${weeklyData.stats?.study_days || 0} 天`, color: 'text-orange-500', bg: 'bg-orange-50' },
                { icon: MessageCircle, label: '场景对话', value: `${weeklyData.stats?.total_dialogs || 0} 次`, color: 'text-purple-500', bg: 'bg-purple-50' },
                { icon: Mic, label: '发音均分', value: `${weeklyData.stats?.avg_pronunciation || 0} 分`, color: 'text-pink-500', bg: 'bg-pink-50' },
                { icon: Star, label: '新词汇', value: `${weeklyData.stats?.total_new_words || 0} 个`, color: 'text-yellow-500', bg: 'bg-yellow-50' },
              ].map((s, i) => (
                <div key={i} className={`card flex flex-col items-center py-4 ${s.bg}`}>
                  <s.icon size={20} className={`${s.color} mb-1`} />
                  <span className="text-lg font-bold">{s.value}</span>
                  <span className="text-xs text-gray-500">{s.label}</span>
                </div>
              ))}
            </div>

            {/* 亮点 */}
            {weeklyData.highlights?.length > 0 && (
              <div className="card">
                <h3 className="font-semibold flex items-center gap-2 mb-3">
                  <Star size={16} className="text-yellow-500" /> 亮点
                </h3>
                <div className="space-y-2">
                  {weeklyData.highlights.map((h: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-green-500 mt-0.5">✦</span>
                      <span className="text-gray-700">{h}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 待改进 */}
            {weeklyData.weaknesses?.length > 0 && (
              <div className="card">
                <h3 className="font-semibold flex items-center gap-2 mb-3">
                  <AlertTriangle size={16} className="text-orange-500" /> 待改进
                </h3>
                <div className="space-y-2">
                  {weeklyData.weaknesses.map((w: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-orange-500 mt-0.5">•</span>
                      <span className="text-gray-700">{w}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 下周建议 */}
            {weeklyData.next_week_suggestions?.length > 0 && (
              <div className="card">
                <h3 className="font-semibold flex items-center gap-2 mb-3">
                  <Calendar size={16} className="text-blue-500" /> 下周建议
                </h3>
                <div className="space-y-2">
                  {weeklyData.next_week_suggestions.map((s: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-blue-500 font-bold">{i + 1}.</span>
                      <span className="text-gray-700">{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="card text-center py-12">
            <Calendar size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">暂无周报数据</p>
            <p className="text-xs text-gray-400 mt-1">请先完成能力诊断，开始学习后每周日自动生成周报</p>
          </div>
        )}
      </>
      )}
    </div>
  )
}
