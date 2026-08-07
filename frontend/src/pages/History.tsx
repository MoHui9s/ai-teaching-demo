import { useEffect, useState } from 'react'
import { tasks } from '../api/client'
import { ChevronDown, ChevronUp, ChevronLeft, Calendar, CheckCircle2, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function History() {
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedDay, setExpandedDay] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const res = await tasks.getHistory(30)
      if (res?.data?.tasks) setHistory(res.data.tasks)
    } catch (e) {
      console.error('加载历史失败', e)
    }
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="p-5 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/3" />
        <div className="h-20 bg-gray-200 rounded-2xl" />
      </div>
    )
  }

  // 按日期分组
  const grouped = history.reduce((acc: Record<string, any[]>, t: any) => {
    const day = t.date || '未知'
    if (!acc[day]) acc[day] = []
    acc[day].push(t)
    return acc
  }, {})

  const days = Object.keys(grouped).sort().reverse()

  // 计算趋势数据
  const trendData = days.slice(0, 14).reverse().map(day => {
    const tasks = grouped[day]
    const totalDone = tasks.reduce((sum: number, t: any) => {
      return sum + (t.task_content?.filter((c: any) => c.status === 'done').length || 0)
    }, 0)
    const totalAll = tasks.reduce((sum: number, t: any) => {
      return sum + (t.task_content?.length || 0)
    }, 0)
    const minutes = tasks.reduce((sum: number, t: any) => sum + (t.time_spent || 0), 0)
    return { day, totalDone, totalAll, minutes }
  })

  const maxMinutes = Math.max(...trendData.map(d => d.minutes), 1)

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="p-1.5 text-gray-400 hover:text-gray-600">
          <ChevronLeft size={20} />
        </button>
        <h1 className="page-title">学习历史</h1>
      </div>

      {/* 趋势图 */}
      {trendData.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <Calendar size={16} className="text-primary-500" />
            近 14 天学习分钟数
          </h3>
          <div className="flex items-end justify-between gap-1 h-24">
            {trendData.map((d, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex items-end justify-center" style={{ height: 64 }}>
                  <div
                    className="w-full max-w-[20px] rounded-t-sm transition-all"
                    style={{
                      height: `${Math.max((d.minutes / maxMinutes) * 56, 3)}px`,
                      backgroundColor: d.totalDone === d.totalAll && d.totalAll > 0 ? '#22c55e' : '#3b82f6',
                    }}
                  />
                </div>
                <span className="text-[10px] text-gray-400">{d.day.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 日期列表 */}
      {days.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">
          <Calendar size={40} className="mx-auto text-gray-300 mb-3" />
          <p>暂无学习记录</p>
          <p className="text-xs mt-1">完成每日任务后会在这里显示</p>
        </div>
      ) : (
        <div className="space-y-3">
          {days.map(day => {
            const dayTasks = grouped[day]
            const isExpanded = expandedDay === day
            const totalDone = dayTasks.reduce((sum: number, t: any) => {
              return sum + (t.task_content?.filter((c: any) => c.status === 'done').length || 0)
            }, 0)
            const totalAll = dayTasks.reduce((sum: number, t: any) => {
              return sum + (t.task_content?.length || 0)
            }, 0)
            const minutes = dayTasks.reduce((sum: number, t: any) => sum + (t.time_spent || 0), 0)
            const allDone = totalAll > 0 && totalDone === totalAll

            return (
              <div key={day} className="card">
                <button
                  onClick={() => setExpandedDay(isExpanded ? null : day)}
                  className="w-full flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      allDone ? 'bg-green-100' : 'bg-gray-100'
                    }`}>
                      <CheckCircle2 size={18} className={allDone ? 'text-green-600' : 'text-gray-400'} />
                    </div>
                    <div className="text-left">
                      <div className="font-medium text-sm">{day}</div>
                      <div className="text-xs text-gray-500">
                        {totalDone}/{totalAll} 任务 · {minutes} 分钟
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {allDone && <span className="text-[10px] px-2 py-0.5 bg-green-100 text-green-600 rounded-full">已完成</span>}
                    {isExpanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                  </div>
                </button>

                {/* 展开任务详情 */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                    {dayTasks.map((t: any, ti: number) => (
                      <div key={ti} className="bg-gray-50 rounded-xl p-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <Clock size={12} /> {t.time_spent || 0} 分钟
                          </span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                            t.status === 'completed' ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {t.status === 'completed' ? '已完成' : '进行中'}
                          </span>
                        </div>
                        {(t.task_content || []).map((c: any, ci: number) => (
                          <div key={ci} className="flex items-center gap-2 text-sm py-1">
                            <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
                              c.status === 'done' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
                            }`}>
                              {c.status === 'done' ? '✓' : ci + 1}
                            </div>
                            <span className={c.status === 'done' ? 'line-through text-gray-400' : 'text-gray-700'}>
                              {c.title}
                            </span>
                            <span className="text-xs text-gray-400 ml-auto">{c.duration_min}min</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
