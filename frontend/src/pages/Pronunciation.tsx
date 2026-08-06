import { useState, useRef } from 'react'
import { pronunciation, tts } from '../api/client'
import { Mic, Square, Play, AlertTriangle } from 'lucide-react'

const SAMPLE_TEXTS = [
  "I think this is a great opportunity.",
  "The weather is very nice today.",
  "Could you tell me how to get to the station?",
  "She sells seashells by the seashore.",
  "I would like a cup of coffee please.",
]

export default function Pronunciation() {
  const [text, setText] = useState(SAMPLE_TEXTS[0])
  const [recording, setRecording] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [playingDemo, setPlayingDemo] = useState(false)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const startRecording = async () => {
    setError('')
    setResult(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      const chunks: Blob[] = []

      recorder.ondataavailable = (e) => chunks.push(e.data)
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const reader = new FileReader()
        reader.onloadend = async () => {
          const base64 = (reader.result as string).split(',')[1]
          setEvaluating(true)
          try {
            const res = await pronunciation.evaluate(text, base64)
            setResult(res)
          } catch (e: any) {
            setError(e.message || '评估失败')
          }
          setEvaluating(false)
        }
        reader.readAsDataURL(blob)
      }

      mediaRecorder.current = recorder
      recorder.start()
      setRecording(true)
    } catch (e: any) {
      setError('无法访问麦克风: ' + (e.message || '权限被拒绝'))
    }
  }

  const stopRecording = () => {
    mediaRecorder.current?.stop()
    setRecording(false)
  }

  const playDemo = async () => {
    if (audioRef.current) {
      audioRef.current.play()
      return
    }
    setPlayingDemo(true)
    try {
      const res = await tts.getAudio(text, 'en-US-AriaNeural', '-10%')
      const audio = new Audio(res.audio_url)
      audioRef.current = audio
      audio.play()
    } catch (e) {
      console.error('播放示范音频失败', e)
    }
    setPlayingDemo(false)
  }

  const scoreColor = (score: number) => {
    if (score >= 80) return 'text-green-500'
    if (score >= 60) return 'text-yellow-500'
    return 'text-red-500'
  }

  return (
    <div className="p-5 space-y-5">
      <h1 className="page-title">发音练习</h1>
      <p className="page-subtitle">跟读模式：听示范 → 朗读 → AI 逐词评分</p>

      {/* 文本选择 */}
      <div className="card">
        <label className="text-sm font-medium mb-2 block">练习文本</label>
        <select
          className="input-field"
          value={text}
          onChange={e => { setText(e.target.value); setResult(null) }}
        >
          {SAMPLE_TEXTS.map((t, i) => (
            <option key={i} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3">
        <button
          onClick={playDemo}
          disabled={playingDemo}
          className="btn-secondary flex-1 flex items-center justify-center gap-2"
        >
          <Play size={18} />
          播放示范
        </button>
        <button
          onClick={recording ? stopRecording : startRecording}
          disabled={evaluating}
          className={`flex-1 flex items-center justify-center gap-2 rounded-xl py-3 font-medium text-white transition-all ${
            recording
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-primary-500 hover:bg-primary-600'
          }`}
        >
          {recording ? (
            <>
              <Square size={18} />
              停止录音
            </>
          ) : evaluating ? (
            <>
              <span className="animate-spin">⏳</span>
              评估中...
            </>
          ) : (
            <>
              <Mic size={18} />
              开始朗读
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="card bg-red-50 border-red-100 flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* 评估结果 */}
      {result && (
        <div className="space-y-4">
          {/* 总分 */}
          <div className="card text-center">
            <div className={`text-5xl font-bold ${scoreColor(result.overall_score)}`}>
              {result.overall_score}
            </div>
            <div className="text-sm text-gray-500 mt-1">总分</div>
            <div className="flex justify-center gap-6 mt-3">
              <div>
                <div className="text-lg font-semibold">{result.accuracy_score}</div>
                <div className="text-xs text-gray-400">准确度</div>
              </div>
              <div>
                <div className="text-lg font-semibold">{result.fluency_score}</div>
                <div className="text-xs text-gray-400">流利度</div>
              </div>
            </div>
          </div>

          {/* 逐词评分 */}
          {result.word_scores?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-3">逐词评分</h3>
              <div className="flex flex-wrap gap-2">
                {result.word_scores.map((w: any, i: number) => (
                  <div key={i} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                    w.score >= 80 ? 'bg-green-100 text-green-700' :
                    w.score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {w.word} <span className="text-xs">({w.score})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 问题音素 */}
          {result.wrong_phonemes?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-3 text-orange-600">需要改进的音素</h3>
              <div className="space-y-2">
                {result.wrong_phonemes.map((p: any, i: number) => (
                  <div key={i} className="bg-orange-50 rounded-xl p-3">
                    <div className="flex items-center gap-2">
                      <span className="bg-orange-200 text-orange-800 px-2 py-0.5 rounded text-sm font-mono font-bold">
                        /{p.phoneme}/
                      </span>
                      <span className="text-sm text-gray-600">在 "{p.word}" 中</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{p.suggestion}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 鼓励语 */}
          <div className="card bg-blue-50 border-blue-100">
            <p className="text-sm text-blue-700">{result.encouragement}</p>
          </div>
        </div>
      )}
    </div>
  )
}
