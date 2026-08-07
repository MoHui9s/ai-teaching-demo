import { useEffect, useState } from 'react'
import { tasks, tts } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { Flame, Clock, Target, BookOpen, ChevronRight, Sparkles, Mic, MessageCircle, LogOut, BookMarked, FileText } from 'lucide-react'
import OnboardingGuide from '../components/OnboardingGuide'
import StudyTimer from '../components/StudyTimer'

interface DashboardProps {
  onLogout: () => void
  todayMinutes: number
}

export default function Dashboard({ onLogout, todayMinutes }: DashboardProps) {
  const [dailyTasks, setDailyTasks] = useState<any>(null)
  const [progress, setProgress] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [voices, setVoices] = useState<Record<string, { name: string; lang: string }>>({})
  const [ttsVoice, setTtsVoice] = useState(localStorage.getItem('tts_voice') || 'en-US-AriaNeural')
  const [history, setHistory] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      tasks.getDaily().catch(() => null),
      fetch('/api/progress/overview').then(r => r.json()).catch(() => null),
      tts.getVoices().then(r => setVoices(r.voices || {})).catch(() => {}),
      tasks.getHistory(7).then(r => {
        if (r?.data?.tasks) setHistory(r.data.tasks)
      }).catch(() => {}),
    ]).then(([taskData, progressData]) => {
      if (taskData?.data) setDailyTasks(taskData.data)
      if (progressData?.data) setProgress(progressData.data)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div className="p-5 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/2" />
        <div className="h-32 bg-gray-200 rounded-2xl" />
        <div className="h-24 bg-gray-200 rounded-2xl" />
      </div>
    )
  }

  const streak = progress?.streak_days || 0
  const taskContent = dailyTasks?.task_content || []
  const completed = taskContent.filter((t: any) => t.status === 'done').length
  const isNewUser = dailyTasks?.onboarding === true
  const hasNoProgress = !progress || (progress.streak_days === 0 && !progress.week_total_minutes)

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">你好，Tan同学 👋</h1>
          <p className="page-subtitle">今天也要加油学英语哦！</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-orange-50 text-orange-600 px-3 py-1.5 rounded-full">
            <Flame size={18} />
            <span className="font-bold text-sm">{streak} 天</span>
          </div>
          <select
            value={ttsVoice}
            onChange={e => { setTtsVoice(e.target.value); localStorage.setItem('tts_voice', e.target.value) }}
            className="text-xs bg-gray-50 border-0 rounded-lg px-2 py-1.5 text-gray-600 max-w-[120px]"
          >
            {Object.entries(voices).length === 0 && (
              <option value="en-US-AriaNeural">Aria (US)</option>
            )}
            {Object.entries(voices).map(([k, v]) => (
              <option key={k} value={k}>{v.name.split(' - ')[1] || v.name}</option>
            ))}
          </select>
          <button
            onClick={onLogout}
            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="退出登录"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>

      {/* 新用户引导 */}
      {(isNewUser || hasNoProgress) && (
        <OnboardingGuide onStartDiagnosis={() => navigate('/diagnosis')} />
      )}

      {/* 今日统计卡片 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="card flex flex-col items-center py-4">
          <Clock size={20} className="text-primary-500 mb-1" />
          <span className="text-xl font-bold">{todayMinutes}</span>
          <span className="text-xs text-gray-500">分钟</span>
        </div>
        <div className="card flex flex-col items-center py-4">
          <Target size={20} className="text-green-500 mb-1" />
          <span className="text-xl font-bold">{completed}/{taskContent.length}</span>
          <span className="text-xs text-gray-500">任务</span>
        </div>
        <div className="card flex flex-col items-center py-4">
          <BookOpen size={20} className="text-accent-500 mb-1" />
          <span className="text-xl font-bold">{progress?.week_total_minutes || 0}</span>
          <span className="text-xs text-gray-500">本周(分)</span>
        </div>
      </div>

      {/* 今日任务 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <Sparkles size={18} className="text-primary-500" />
            今日任务
          </h3>
          <button onClick={() => navigate('/tasks')} className="text-primary-500 text-sm flex items-center gap-1">
            详情 <ChevronRight size={14} />
          </button>
        </div>
        <div className="space-y-3">
          {taskContent.map((task: any, i: number) => (
            <div key={i} className={`flex items-center gap-3 p-3 rounded-xl ${
              task.status === 'done' ? 'bg-green-50' : 'bg-gray-50'
            }`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                task.status === 'done' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
              }`}>
                {task.status === 'done' ? '✓' : i + 1}
              </div>
              <div className="flex-1 text-sm">
                <span className={task.status === 'done' ? 'line-through text-gray-400' : ''}>
                  {task.title}
                </span>
              </div>
              <span className="text-xs text-gray-400">{task.duration_min}min</span>
            </div>
          ))}
        </div>
      </div>

      {/* 快捷入口 */}
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <button onClick={() => navigate('/diagnosis')} className="card flex items-center gap-3 hover:bg-blue-50 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <Target size={20} className="text-blue-600" />
            </div>
            <div className="text-left">
              <div className="font-medium text-sm">能力诊断</div>
              <div className="text-xs text-gray-500">了解水平</div>
            </div>
          </button>
          <button onClick={() => navigate('/scenario')} className="card flex items-center gap-3 hover:bg-purple-50 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
              <MessageCircle size={20} className="text-purple-600" />
            </div>
            <div className="text-left">
              <div className="font-medium text-sm">场景对话</div>
              <div className="text-xs text-gray-500">10+ 场景</div>
            </div>
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <button onClick={() => navigate('/vocab')} className="card flex items-center gap-3 hover:bg-orange-50 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center">
              <BookMarked size={20} className="text-orange-600" />
            </div>
            <div className="text-left">
              <div className="font-medium text-sm">词汇学习</div>
              <div className="text-xs text-gray-500">闪卡记忆</div>
            </div>
          </button>
          <button onClick={() => navigate('/reading')} className="card flex items-center gap-3 hover:bg-green-50 transition-colors">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
              <FileText size={20} className="text-green-600" />
            </div>
            <div className="text-left">
              <div className="font-medium text-sm">阅读训练</div>
              <div className="text-xs text-gray-500">分级短文</div>
            </div>
          </button>
        </div>
      </div>

      {/* 近 7 天完成趋势 */}
      {history.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">近 7 天完成情况</h3>
            <button onClick={() => navigate('/history')} className="text-primary-500 text-xs flex items-center gap-1">
              查看全部 <ChevronRight size={12} />
            </button>
          </div>
          <div className="flex items-end justify-between gap-1 h-16">
            {history.map((t: any, i: number) => {
              const done = t.task_content?.filter((c: any) => c.status === 'done').length || 0
              const total = t.task_content?.length || 3
              const pct = total > 0 ? (done / total) * 100 : 0
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex items-end justify-center" style={{ height: 48 }}>
                    <div
                      className="w-full max-w-[24px] rounded-t-sm transition-all"
                      style={{
                        height: `${Math.max(pct * 0.4, 4)}px`,
                        backgroundColor: pct === 100 ? '#22c55e' : pct > 0 ? '#3b82f6' : '#e5e7eb',
                      }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-400">{t.date?.slice(5) || '-'}</span>
                </div>
              )
            })}
          </div>
          <div className="flex items-center justify-between mt-2 text-[10px] text-gray-400">
            <span>{history.length} 天前</span>
            <span>今天</span>
          </div>
        </div>
      )}
    </div>
  )
}
