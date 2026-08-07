import { useState } from 'react'
import { tasks } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight } from 'lucide-react'
import AudioPlayButton from '../components/AudioPlayButton'

// 简易诊断题目
const VOCAB_QUESTIONS = [
  { word: 'apple', hint: '一种常见的水果' },
  { word: 'beautiful', hint: '用来形容好看的人或物' },
  { word: 'important', hint: '表示某件事很关键、不能忽视' },
]

const LISTENING_QUESTIONS = [
  { question: '听到 "Hello, how are you?" 应该回答？', options: ['I\'m fine, thank you', 'My name is Tom', 'Goodbye'], answer: 0, audio: 'Hello, how are you?' },
  { question: '听到 "What time is it?" 在问什么？', options: ['日期', '时间', '天气'], answer: 1, audio: 'What time is it?' },
]

export default function Diagnosis() {
  const [step, setStep] = useState<'intro' | 'vocab' | 'listening' | 'result'>('intro')
  const [vocabAnswers, setVocabAnswers] = useState<string[]>(['', '', ''])
  const [listeningAnswers, setListeningAnswers] = useState<string[]>([])
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleStart = () => setStep('vocab')

  const handleVocabSubmit = () => {
    setStep('listening')
  }

  const handleListeningSelect = (qIndex: number, optIndex: number) => {
    const newAnswers = [...listeningAnswers]
    newAnswers[qIndex] = LISTENING_QUESTIONS[qIndex].options[optIndex]
    setListeningAnswers(newAnswers)
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const res = await tasks.diagnose({
        vocab_answers: vocabAnswers.filter(Boolean),
        pronunciation_text: 'hello',
        listening_answers: listeningAnswers.filter(Boolean),
      })
      setResult(res)
      setStep('result')
    } catch (err: any) {
      console.error('诊断失败:', err)
    } finally {
      setLoading(false)
    }
  }

  if (step === 'intro') {
    return (
      <div className="p-5 space-y-6">
        <div className="text-center py-8">
          <div className="text-6xl mb-4">🎯</div>
          <h2 className="text-2xl font-bold mb-2">英语能力诊断</h2>
          <p className="text-gray-500 text-sm">5分钟快速测试，了解你的当前水平，定制专属学习计划</p>
        </div>
        <div className="card space-y-3">
          <div className="flex items-center gap-3 text-sm">
            <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">1</span>
            <span>单词填空（3题）—— 测词汇量</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">2</span>
            <span>听力选择（2题）—— 测听力理解</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">3</span>
            <span>获取等级 + 定制任务</span>
          </div>
        </div>
        <button onClick={handleStart} className="btn-primary w-full flex items-center justify-center gap-2">
          开始诊断 <ArrowRight size={18} />
        </button>
      </div>
    )
  }

  if (step === 'vocab') {
    return (
      <div className="p-5 space-y-5">
        <h2 className="text-xl font-bold">📝 单词填空</h2>
        <p className="text-sm text-gray-500">根据提示写出对应的英文单词（不会可以跳过）</p>
        <div className="space-y-4">
          {VOCAB_QUESTIONS.map((q, i) => (
            <div key={i} className="card">
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm text-gray-500">
                  提示：{q.hint}
                </label>
                <AudioPlayButton text={q.word} size={16} />
              </div>
              <input
                type="text"
                className="input-field"
                value={vocabAnswers[i]}
                onChange={e => {
                  const newAnswers = [...vocabAnswers]
                  newAnswers[i] = e.target.value
                  setVocabAnswers(newAnswers)
                }}
                placeholder="输入英文单词..."
              />
            </div>
          ))}
        </div>
        <button onClick={handleVocabSubmit} className="btn-primary w-full">
          下一步
        </button>
      </div>
    )
  }

  if (step === 'listening') {
    return (
      <div className="p-5 space-y-5">
        <h2 className="text-xl font-bold">🎧 听力选择</h2>
        <p className="text-sm text-gray-500">阅读问题并选择正确答案</p>
        <div className="space-y-4">
          {LISTENING_QUESTIONS.map((q, qi) => (
            <div key={qi} className="card">
              <div className="flex items-center justify-between mb-3">
                <p className="font-medium">{q.question}</p>
                <AudioPlayButton text={q.audio} size={16} />
              </div>
              <div className="space-y-2">
                {q.options.map((opt, oi) => (
                  <button
                    key={oi}
                    className={`w-full text-left p-2 rounded-lg text-sm transition-colors ${
                      listeningAnswers[qi] === opt
                        ? 'bg-primary-100 text-primary-700 font-medium'
                        : 'bg-gray-50 hover:bg-gray-100'
                    }`}
                    onClick={() => handleListeningSelect(qi, oi)}
                  >
                    {String.fromCharCode(65 + oi)}. {opt}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="btn-primary w-full"
        >
          {loading ? '评估中...' : '提交诊断'}
        </button>
      </div>
    )
  }

  // Result
  return (
    <div className="p-5 space-y-6">
      <div className="text-center py-6">
        <div className="text-5xl mb-4">{result?.level === 'beginner' ? '🌱' : result?.level === 'intermediate' ? '🌿' : '🌳'}</div>
        <h2 className="text-2xl font-bold mb-1">诊断完成！</h2>
        <p className="text-primary-600 font-medium text-lg">{result?.message || ''}</p>
      </div>
      {result && (
        <div className="card space-y-3">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-2xl font-bold text-primary-500">{result.vocab_estimate}</div>
              <div className="text-xs text-gray-500">词汇量</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-500">{result.pronunciation_estimate}</div>
              <div className="text-xs text-gray-500">发音分</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent-500">{result.listening_estimate}</div>
              <div className="text-xs text-gray-500">听力分</div>
            </div>
          </div>
        </div>
      )}
      <button onClick={() => navigate('/tasks')} className="btn-primary w-full flex items-center justify-center gap-2">
        <Sparkles size={18} /> 查看今日任务
      </button>
    </div>
  )
}
