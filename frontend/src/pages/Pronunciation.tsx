import { useState } from 'react'
import { ChevronLeft, Mic, Volume2, CheckCircle, XCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import AudioPlayButton from '../components/AudioPlayButton'
import VoiceInputButton from '../components/VoiceInputButton'

const PRESET_SENTENCES: Record<string, string[]> = {
  beginner: [
    'Hello, how are you today?',
    'I like to read books in the morning.',
    'The weather is very nice today.',
    'My family and I went to the park.',
    'Can you help me with this problem?',
    'She is my best friend at school.',
  ],
  intermediate: [
    'I have been studying English for three years.',
    'Would you like to join us for dinner tonight?',
    'The movie was interesting, but the ending was disappointing.',
    'If I had more time, I would travel around the world.',
    'She suggested that we should start earlier tomorrow.',
    'Could you explain that again? I did not quite understand.',
  ],
  advanced: [
    'The rapid advancement of technology has fundamentally changed how we communicate.',
    'Despite numerous challenges, the team persevered and eventually achieved their goal.',
    'It is widely acknowledged that climate change poses a significant threat.',
    'Her comprehensive analysis of the situation proved to be remarkably accurate.',
    'The negotiation process was complex, but ultimately both parties reached a consensus.',
    'I would argue that the benefits significantly outweigh the potential drawbacks.',
  ],
}

export default function Pronunciation() {
  const [level, setLevel] = useState('beginner')
  const [customText, setCustomText] = useState('')
  const [referenceText, setReferenceText] = useState('')
  const [transcript, setTranscript] = useState('')
  const [assessResult, setAssessResult] = useState<any>(null)
  const [assessing, setAssessing] = useState(false)
  const navigate = useNavigate()

  const sentence = referenceText || PRESET_SENTENCES[level][0]

  const selectPreset = (text: string) => {
    setReferenceText(text)
    setTranscript('')
    setAssessResult(null)
  }

  const handleAssess = async () => {
    if (!transcript.trim()) return
    setAssessing(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE || ''}/api/tasks/pronunciation/assess-text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('edulingua_token')}`,
        },
        body: JSON.stringify({ transcript: transcript.trim(), reference_text: sentence }),
      })
      if (res.ok) {
        const data = await res.json()
        setAssessResult(data.data)
      }
    } catch (e) {
      console.error('评估失败', e)
    }
    setAssessing(false)
  }

  const levelLabels: Record<string, string> = {
    beginner: '初级', intermediate: '中级', advanced: '高级',
  }

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="p-1.5 text-gray-400 hover:text-gray-600">
          <ChevronLeft size={20} />
        </button>
        <h1 className="page-title">发音练习</h1>
      </div>

      {/* 级别切换 */}
      <div className="flex gap-2">
        {Object.entries(levelLabels).map(([k, v]) => (
          <button
            key={k}
            onClick={() => { setLevel(k); setReferenceText(''); setTranscript(''); setAssessResult(null) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              level === k ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {/* 预设句子选择 */}
      <div className="card">
        <h3 className="text-sm font-medium mb-3">选择练习句</h3>
        <div className="space-y-2">
          {PRESET_SENTENCES[level].map((s, i) => (
            <button
              key={i}
              onClick={() => selectPreset(s)}
              className={`w-full text-left p-3 rounded-xl text-sm transition-colors ${
                referenceText === s
                  ? 'bg-primary-50 border border-primary-200 text-primary-700'
                  : 'bg-gray-50 hover:bg-gray-100 text-gray-700'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* 自定义输入 */}
      <div className="card">
        <h3 className="text-sm font-medium mb-2">或自定义句子</h3>
        <textarea
          value={customText}
          onChange={e => setCustomText(e.target.value)}
          onBlur={() => {
            if (customText.trim()) {
              setReferenceText(customText.trim())
              setTranscript('')
              setAssessResult(null)
            }
          }}
          placeholder="输入你想练习的英文句子..."
          className="input-field w-full h-16 resize-none text-sm"
        />
      </div>

      {/* 当前练习句 */}
      {referenceText && (
        <div className="card bg-blue-50">
          <p className="text-xs text-blue-500 mb-1">当前练习句</p>
          <p className="text-lg font-semibold text-blue-800">{sentence}</p>
          <div className="flex items-center gap-3 mt-3">
            <span className="text-xs text-gray-500">范读:</span>
            <AudioPlayButton text={sentence} size={20} />
          </div>
        </div>
      )}

      {/* 录音区 */}
      {referenceText && (
        <div className="card">
          <h3 className="text-sm font-medium mb-3">跟读录音</h3>
          <div className="flex items-center gap-3">
            <VoiceInputButton
              onTranscript={(text) => {
                setTranscript(text)
                setAssessResult(null)
              }}
              size={24}
            />
            <span className="text-xs text-gray-500">点击麦克风开始录音跟读</span>
          </div>

          {transcript && (
            <div className="mt-3 bg-blue-50 rounded-xl p-3">
              <p className="text-xs text-blue-500 mb-1">识别结果:</p>
              <p className="text-sm text-blue-800">{transcript}</p>
            </div>
          )}

          {transcript && !assessResult && (
            <button
              onClick={handleAssess}
              disabled={assessing}
              className="mt-3 w-full py-2.5 bg-primary-500 text-white rounded-xl text-sm font-medium hover:bg-primary-600 disabled:opacity-50"
            >
              {assessing ? '评估中...' : '🔍 检查发音'}
            </button>
          )}
        </div>
      )}

      {/* 评估结果 */}
      {assessResult && (
        <div className={`card ${assessResult.score >= 80 ? 'bg-green-50' : assessResult.score >= 50 ? 'bg-yellow-50' : 'bg-red-50'}`}>
          <h3 className="text-sm font-medium mb-3">评估结果</h3>

          {/* 分数 */}
          <div className="flex items-center gap-3 mb-3">
            <span className="text-3xl font-bold">{assessResult.score}</span>
            <span className="text-sm text-gray-500">/ 100 分</span>
          </div>

          {/* 转写文本 */}
          <div className="bg-white rounded-lg p-3 mb-3">
            <p className="text-xs text-gray-400 mb-1">你说的是</p>
            <p className="text-sm">{assessResult.transcript}</p>
          </div>

          {/* 参考文本 */}
          <div className="bg-white rounded-lg p-3 mb-3">
            <p className="text-xs text-gray-400 mb-1">参考文本</p>
            <p className="text-sm">{assessResult.reference_text}</p>
          </div>

          {/* 匹配词 */}
          {assessResult.matched_words?.length > 0 && (
            <div className="flex items-start gap-2 mb-2">
              <CheckCircle size={16} className="text-green-500 mt-0.5 shrink-0" />
              <p className="text-xs text-green-700">
                正确: <span className="font-medium">{assessResult.matched_words.join(', ')}</span>
              </p>
            </div>
          )}

          {/* 遗漏词 */}
          {assessResult.missing_words?.length > 0 && (
            <div className="flex items-start gap-2 mb-2">
              <XCircle size={16} className="text-red-500 mt-0.5 shrink-0" />
              <p className="text-xs text-red-700">
                遗漏: <span className="font-medium">{assessResult.missing_words.join(', ')}</span>
              </p>
            </div>
          )}

          {/* 多余词 */}
          {assessResult.extra_words?.length > 0 && (
            <div className="flex items-start gap-2">
              <XCircle size={16} className="text-orange-500 mt-0.5 shrink-0" />
              <p className="text-xs text-orange-700">
                多余: <span className="font-medium">{assessResult.extra_words.join(', ')}</span>
              </p>
            </div>
          )}

          {/* 重试按钮 */}
          <button
            onClick={() => { setTranscript(''); setAssessResult(null) }}
            className="mt-4 text-xs text-primary-500 hover:text-primary-700 font-medium"
          >
            🔄 再试一次
          </button>
        </div>
      )}

      {/* 空状态提示 */}
      {!referenceText && (
        <div className="card text-center py-12 text-gray-500">
          <Mic size={40} className="mx-auto text-gray-300 mb-3" />
          <p>选择或输入一个句子开始练习</p>
          <p className="text-xs mt-1">先听范读 → 录音跟读 → 检查发音</p>
        </div>
      )}
    </div>
  )
}
