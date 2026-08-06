import { useState, useEffect } from 'react'
import { scenarios } from '../api/client'
import { MessageCircle, Send, Camera } from 'lucide-react'

const DIFFICULTIES = [
  { value: 'easy', label: '简单', color: 'bg-green-100 text-green-700' },
  { value: 'medium', label: '中等', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'hard', label: '困难', color: 'bg-red-100 text-red-700' },
]

export default function ScenarioChat() {
  const [sceneList, setSceneList] = useState<any[]>([])
  const [selectedScene, setSelectedScene] = useState('restaurant')
  const [selectedDifficulty, setSelectedDifficulty] = useState('easy')
  const [started, setStarted] = useState(false)
  const [opening, setOpening] = useState('')
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState('')

  useEffect(() => {
    scenarios.list().then(res => {
      if (res?.data?.scenarios) setSceneList(res.data.scenarios)
    }).catch(() => {})
  }, [])

  const handleStart = async () => {
    try {
      const res = await scenarios.start(selectedScene, selectedDifficulty)
      if (res?.data) {
        setOpening(res.data.opening_prompt || '')
        setStarted(true)
        setMessages([])
        setInput('')
      }
    } catch (e) {
      console.error('启动场景失败', e)
    }
  }

  const handleSend = () => {
    if (!input.trim()) return
    setMessages(prev => [...prev, { role: 'user', content: input }])
    // 模拟 NPC 回复（实际应调用 chat completions）
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `📢 NPC: ${input.includes('?') ? "That's a good question!" : "I see. Let me help you with that."}\n\n📝 教师提示: This is a good starting point — keep practicing! | 这是一个不错的开始——继续练习！`
      }])
    }, 800)
    setInput('')
  }

  if (!started) {
    return (
      <div className="p-5 space-y-5">
        <h1 className="page-title">场景对话</h1>
        <p className="page-subtitle">选择一个场景，AI 陪你练口语</p>

        {/* 场景选择 */}
        <div className="space-y-3">
          {sceneList.map(scene => (
            <button
              key={scene.id}
              onClick={() => setSelectedScene(scene.id)}
              className={`card w-full text-left flex items-center gap-3 transition-colors ${
                selectedScene === scene.id ? 'ring-2 ring-primary-500 bg-primary-50' : ''
              }`}
            >
              <div className="text-2xl">{scene.icon}</div>
              <div className="flex-1">
                <h3 className="font-medium text-sm">{scene.name}</h3>
                <p className="text-xs text-gray-500">{scene.description}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                DIFFICULTIES.find(d => d.value === scene.difficulty)?.color
              }`}>
                {DIFFICULTIES.find(d => d.value === scene.difficulty)?.label}
              </span>
            </button>
          ))}
        </div>

        {/* 难度选择 */}
        <div className="card">
          <label className="text-sm font-medium mb-2 block">难度选择</label>
          <div className="flex gap-2">
            {DIFFICULTIES.map(d => (
              <button
                key={d.value}
                onClick={() => setSelectedDifficulty(d.value)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  selectedDifficulty === d.value
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <button onClick={handleStart} className="btn-primary w-full flex items-center justify-center gap-2">
          <MessageCircle size={18} />
          开始对话
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen max-w-lg mx-auto">
      {/* Header */}
      <div className="p-5 border-b bg-white">
        <h1 className="font-semibold">
          {sceneList.find(s => s.id === selectedScene)?.name || '场景对话'}
        </h1>
        <p className="text-xs text-gray-500 mt-1">{opening}</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 text-gray-800'
            }`}>
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            className="input-field flex-1"
            placeholder="输入你的对话..."
          />
          <button onClick={handleSend} className="btn-primary px-4">
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
