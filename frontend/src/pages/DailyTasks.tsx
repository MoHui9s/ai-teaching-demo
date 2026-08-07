import { useEffect, useState } from 'react'
import { tasks } from '../api/client'
import { Clock, CheckCircle2, Circle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import AudioPlayButton from '../components/AudioPlayButton'
import VoiceInputButton from '../components/VoiceInputButton'

export default function DailyTasks() {
  const [taskData, setTaskData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(-1)
  // 听力任务：每个任务独立的听写输入
  const [dictationInputs, setDictationInputs] = useState<Record<number, string>>({})
  // 口语任务：ASR 转写结果
  const [transcripts, setTranscripts] = useState<Record<number, string>>({})
  // 口语任务：发音评估结果
  const [assessResults, setAssessResults] = useState<Record<number, any>>({})
  // 听力任务：听写检查结果
  const [dictationResults, setDictationResults] = useState<Record<number, any>>({})
  // 展开的任务面板
  const [expandedTask, setExpandedTask] = useState<number | null>(null)

  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const res = await tasks.getDaily()
      if (res?.data) setTaskData(res.data)
    } catch (e) {
      console.error('加载任务失败', e)
    }
    setLoading(false)
  }

  const handleComplete = async (index: number) => {
    setCompleting(index)
    try {
      const res = await tasks.complete(index, taskData.task_content[index].duration_min)
      if (res?.data) setTaskData(res.data)
    } catch (e) {
      console.error('完成任务失败', e)
    }
    setCompleting(-1)
  }

  const toggleExpand = (index: number) => {
    setExpandedTask(prev => prev === index ? null : index)
  }

  const handleAssess = async (index: number, referenceText: string) => {
    // 需要重新录音来获取 Blob — 这里从 useVoiceRecorder 无法直接拿到 Blob
    // 改为用 transcripts[index] 作为输入直接调文字比对
    // 简化方案：将 transcript 作为 user_input 发给后端
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE || ''}/api/tasks/pronunciation/assess-text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('edulingua_token')}`,
        },
        body: JSON.stringify({ transcript: transcripts[index], reference_text: referenceText }),
      })
      if (res.ok) {
        const data = await res.json()
        setAssessResults(prev => ({ ...prev, [index]: data.data }))
      }
    } catch (e) {
      console.error('评估失败', e)
    }
  }

  const handleCheckDictation = async (index: number, referenceText: string) => {
    const userInput = dictationInputs[index] || ''
    if (!userInput.trim()) return
    try {
      const res = await tasks.checkDictation(userInput, referenceText)
      if (res?.data) setDictationResults(prev => ({ ...prev, [index]: res.data }))
    } catch (e) {
      console.error('听写检查失败', e)
    }
  }

  if (loading) {
    return (
      <div className="p-5 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/3" />
        <div className="h-20 bg-gray-200 rounded-2xl" />
      </div>
    )
  }

  if (!taskData) {
    return (
      <div className="p-5">
        <h1 className="page-title">每日任务</h1>
        <div className="card text-center py-12">
          <AlertCircle size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">暂无任务数据，请确认后端服务已启动</p>
        </div>
      </div>
    )
  }

  const content = taskData.task_content || []
  const done = content.filter((t: any) => t.status === 'done').length
  const total = content.length
  const progress = total > 0 ? (done / total) * 100 : 0

  const typeIcons: Record<string, string> = {
    vocab: '📝', speaking: '🎤', listening: '👂', reading: '📖', writing: '✍️'
  }

  return (
    <div className="p-5 space-y-5">
      <h1 className="page-title">每日任务</h1>

      {/* 进度条 */}
      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">完成进度</span>
          <span className="text-sm text-gray-500">{done}/{total}</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
          <Clock size={14} />
          <span>今日已学 {taskData.time_spent || 0} 分钟</span>
        </div>
      </div>

      {/* 任务列表 */}
      <div className="space-y-3">
        {content.map((task: any, i: number) => {
          const isExpanded = expandedTask === i
          const isDone = task.status === 'done'
          const isSpeaking = task.type === 'speaking'
          const isListening = task.type === 'listening'

          return (
            <div key={i}>
              <div className={`card ${isDone ? 'bg-green-50 border-green-100' : ''}`}>
                <div className="flex items-center gap-4">
                  <div className="text-2xl">{typeIcons[task.type] || '📌'}</div>
                  <div className="flex-1 min-w-0">
                    <h3 className={`text-sm font-medium ${isDone ? 'line-through text-gray-400' : ''}`}>
                      {task.title}
                    </h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-gray-400 flex items-center gap-1">
                        <Clock size={12} /> {task.duration_min} 分钟
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                        {task.type}
                      </span>
                    </div>
                  </div>

                  {/* 音频按钮 (speaking / listening) */}
                  {!isDone && (isSpeaking || isListening) && (
                    <AudioPlayButton
                      text={task.title.replace(/^[🎤👂📝📖✍️]\s*/, '')}
                      size={16}
                    />
                  )}

                  {/* 展开/收起 + 完成 */}
                  <div className="flex items-center gap-1">
                    {(isSpeaking || isListening) && (
                      <button
                        onClick={() => toggleExpand(i)}
                        className="p-1.5 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    )}
                    <button
                      onClick={() => handleComplete(i)}
                      disabled={isDone || completing === i}
                      className={`p-2 rounded-full transition-colors ${
                        isDone ? 'text-green-500' : 'text-gray-300 hover:text-green-500'
                      }`}
                    >
                      {isDone ? <CheckCircle2 size={28} /> : <Circle size={28} />}
                    </button>
                  </div>
                </div>

                {/* 口语任务交互面板 */}
                {isExpanded && isSpeaking && !isDone && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                    <p className="text-xs text-gray-500">
                      👆 先点喇叭听范读 → 点麦克风录音跟读 → 对比转写结果 → 点右侧圈圈完成
                    </p>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-500">范读:</span>
                      <AudioPlayButton text={task.title} size={20} />
                      <span className="text-xs text-gray-300">|</span>
                      <span className="text-xs text-gray-500">跟读:</span>
                      <VoiceInputButton
                        onTranscript={(text) =>
                          setTranscripts(prev => ({ ...prev, [i]: text }))
                        }
                        size={20}
                      />
                    </div>
                    {transcripts[i] && (
                      <>
                        <div className="bg-blue-50 rounded-xl p-3">
                          <p className="text-xs text-blue-500 mb-1">识别结果:</p>
                          <p className="text-sm text-blue-800 font-medium">{transcripts[i]}</p>
                        </div>
                        <button
                          onClick={() => handleAssess(i, task.title)}
                          className="text-xs text-primary-500 hover:text-primary-700 font-medium"
                        >
                          🔍 检查发音
                        </button>
                      </>
                    )}
                    {assessResults[i] && (
                      <div className={`rounded-xl p-3 ${assessResults[i].score >= 80 ? 'bg-green-50' : assessResults[i].score >= 50 ? 'bg-yellow-50' : 'bg-red-50'}`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg font-bold">{assessResults[i].score} 分</span>
                          <span className="text-xs text-gray-500">
                            ({assessResults[i].matched_words?.length || 0}/{assessResults[i].missing_words?.length || 0 + (assessResults[i].matched_words?.length || 0)} 词匹配)
                          </span>
                        </div>
                        {assessResults[i].missing_words?.length > 0 && (
                          <p className="text-xs text-red-600">
                            遗漏词: <span className="font-medium">{assessResults[i].missing_words.join(', ')}</span>
                          </p>
                        )}
                        {assessResults[i].extra_words?.length > 0 && (
                          <p className="text-xs text-orange-600 mt-1">
                            多余词: <span className="font-medium">{assessResults[i].extra_words.join(', ')}</span>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 听力任务交互面板 */}
                {isExpanded && isListening && !isDone && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                    <p className="text-xs text-gray-500">
                      👆 点喇叭听音频 → 在下方输入听到的内容 → 点右侧圈圈完成
                    </p>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">播放:</span>
                      <AudioPlayButton text={task.title} size={20} rate="-20%" />
                      <span className="text-xs text-gray-400">(慢速)</span>
                    </div>
                    <textarea
                      className="input-field w-full h-20 resize-none text-sm"
                      placeholder="输入你听到的内容..."
                      value={dictationInputs[i] || ''}
                      onChange={e =>
                        setDictationInputs(prev => ({ ...prev, [i]: e.target.value }))
                      }
                    />
                    {dictationInputs[i]?.trim() && (
                      <button
                        onClick={() => handleCheckDictation(i, task.title)}
                        className="text-xs text-primary-500 hover:text-primary-700 font-medium"
                      >
                        ✅ 检查听写
                      </button>
                    )}
                    {dictationResults[i] && (
                      <div className={`rounded-xl p-3 ${dictationResults[i].accuracy >= 80 ? 'bg-green-50' : dictationResults[i].accuracy >= 50 ? 'bg-yellow-50' : 'bg-red-50'}`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg font-bold">{dictationResults[i].accuracy}%</span>
                          <span className="text-xs text-gray-500">
                            ({dictationResults[i].correct_words}/{dictationResults[i].total_words} 正确)
                          </span>
                        </div>
                        {dictationResults[i].errors?.length > 0 && (
                          <div className="space-y-1">
                            {dictationResults[i].errors.map((err: any, ei: number) => (
                              <p key={ei} className="text-xs text-red-600">
                                第{err.position}词: 期望 <span className="font-medium">"{err.expected}"</span>
                                {err.got !== '(缺失)' ? <> → 你写的是 <span className="font-medium">"{err.got}"</span></> : ' → 缺失'}
                              </p>
                            ))}
                          </div>
                        )}
                        {dictationResults[i].missing_count > 0 && (
                          <p className="text-xs text-orange-600 mt-1">漏词 {dictationResults[i].missing_count} 个</p>
                        )}
                        {dictationResults[i].extra_count > 0 && (
                          <p className="text-xs text-orange-600 mt-1">多词 {dictationResults[i].extra_count} 个</p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
