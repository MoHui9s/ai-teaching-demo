import { useEffect, useState, useCallback } from 'react'
import { vocab } from '../api/client'
import { ChevronLeft, ChevronRight, RotateCcw, Check, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import AudioPlayButton from '../components/AudioPlayButton'

interface Word {
  word: string
  chinese: string
  example: string
}

export default function Vocab() {
  const [words, setWords] = useState<Word[]>([])
  const [loading, setLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [level, setLevel] = useState('beginner')
  const [known, setKnown] = useState<Set<string>>(new Set())
  const [unknown, setUnknown] = useState<Set<string>>(new Set())
  const navigate = useNavigate()

  const loadWords = useCallback(async (lvl: string) => {
    setLoading(true)
    setFlipped(false)
    setCurrentIndex(0)
    try {
      const res = await vocab.list(lvl, 20)
      if (res?.data?.words) {
        setWords(res.data.words)
      }
    } catch (e) {
      console.error('加载词汇失败', e)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadWords(level)
  }, [level, loadWords])

  // 恢复已知/未知词（从 localStorage）
  useEffect(() => {
    try {
      const savedKnown = localStorage.getItem(`vocab_known_${level}`)
      const savedUnknown = localStorage.getItem(`vocab_unknown_${level}`)
      if (savedKnown) setKnown(new Set(JSON.parse(savedKnown)))
      if (savedUnknown) setUnknown(new Set(JSON.parse(savedUnknown)))
    } catch { /* ignore */ }
  }, [level])

  const markWord = (type: 'known' | 'unknown') => {
    const word = words[currentIndex]?.word
    if (!word) return

    if (type === 'known') {
      const next = new Set(known)
      next.add(word)
      unknown.delete(word)
      setKnown(next)
      setUnknown(new Set(unknown))
      localStorage.setItem(`vocab_known_${level}`, JSON.stringify([...next]))
      localStorage.setItem(`vocab_unknown_${level}`, JSON.stringify([...unknown]))
    } else {
      const next = new Set(unknown)
      next.add(word)
      known.delete(word)
      setUnknown(next)
      setKnown(new Set(known))
      localStorage.setItem(`vocab_known_${level}`, JSON.stringify([...known]))
      localStorage.setItem(`vocab_unknown_${level}`, JSON.stringify([...next]))
    }

    // 自动跳到下一个
    if (currentIndex < words.length - 1) {
      setTimeout(() => {
        setCurrentIndex(prev => prev + 1)
        setFlipped(false)
      }, 200)
    }
  }

  const handleNext = () => {
    if (currentIndex < words.length - 1) {
      setCurrentIndex(prev => prev + 1)
      setFlipped(false)
    }
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1)
      setFlipped(false)
    }
  }

  const resetProgress = () => {
    setKnown(new Set())
    setUnknown(new Set())
    setCurrentIndex(0)
    setFlipped(false)
    localStorage.removeItem(`vocab_known_${level}`)
    localStorage.removeItem(`vocab_unknown_${level}`)
  }

  // 键盘快捷键
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') markWord('known')
      else if (e.key === 'ArrowRight') markWord('unknown')
      else if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault()
        setFlipped(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [currentIndex, words, known, unknown])

  const currentWord = words[currentIndex]
  const totalKnown = known.size
  const totalUnknown = unknown.size
  const totalReviewed = totalKnown + totalUnknown

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
        <h1 className="page-title">词汇学习</h1>
      </div>

      {/* 级别切换 */}
      <div className="flex gap-2">
        {Object.entries(levelLabels).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setLevel(k)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              level === k
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-48 bg-gray-200 rounded-2xl" />
        </div>
      ) : words.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">
          <p>暂无语汇数据</p>
        </div>
      ) : (
        <>
          {/* 进度 */}
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>{currentIndex + 1} / {words.length}</span>
            <div className="flex items-center gap-4">
              <span className="text-green-600">✅ {totalKnown}</span>
              <span className="text-red-500">❌ {totalUnknown}</span>
              <button onClick={resetProgress} className="text-gray-400 hover:text-gray-600" title="重置">
                <RotateCcw size={14} />
              </button>
            </div>
          </div>

          {/* 进度条 */}
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full transition-all duration-300"
              style={{ width: `${(totalReviewed / words.length) * 100}%` }}
            />
          </div>

          {/* 闪卡 */}
          <div
            onClick={() => setFlipped(!flipped)}
            className={`relative w-full h-56 cursor-pointer select-none transition-transform duration-500 ${
              flipped ? '' : ''
            }`}
            style={{ perspective: '1000px' }}
          >
            <div
              className={`relative w-full h-full transition-all duration-500`}
              style={{
                transformStyle: 'preserve-3d',
                transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
              }}
            >
              {/* 正面：英文单词 */}
              <div
                className="absolute inset-0 card flex flex-col items-center justify-center gap-4"
                style={{ backfaceVisibility: 'hidden' }}
              >
                <span className="text-3xl font-bold text-gray-800">{currentWord?.word}</span>
                <div className="flex items-center gap-2">
                  <AudioPlayButton text={currentWord?.word || ''} size={18} />
                  <span className="text-xs text-gray-400">点击发音</span>
                </div>
                <p className="text-xs text-gray-400 mt-4">点击卡片翻转查看释义</p>
              </div>

              {/* 背面：中文+例句 */}
              <div
                className="absolute inset-0 card flex flex-col items-center justify-center gap-3 bg-primary-50"
                style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
              >
                <span className="text-2xl font-bold text-primary-600">{currentWord?.chinese}</span>
                <p className="text-sm text-gray-600 text-center px-4 italic">
                  "{currentWord?.example}"
                </p>
                <AudioPlayButton text={currentWord?.example || ''} size={16} />
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center justify-between gap-3">
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className="p-3 rounded-full bg-gray-100 text-gray-500 disabled:opacity-30 hover:bg-gray-200 transition-colors"
            >
              <ChevronLeft size={22} />
            </button>

            <button
              onClick={() => markWord('unknown')}
              className="flex-1 py-3 rounded-xl bg-red-50 text-red-600 font-medium flex items-center justify-center gap-2 hover:bg-red-100 transition-colors"
            >
              <X size={18} /> 不认识
            </button>

            <button
              onClick={() => markWord('known')}
              className="flex-1 py-3 rounded-xl bg-green-50 text-green-600 font-medium flex items-center justify-center gap-2 hover:bg-green-100 transition-colors"
            >
              <Check size={18} /> 认识
            </button>

            <button
              onClick={handleNext}
              disabled={currentIndex >= words.length - 1}
              className="p-3 rounded-full bg-gray-100 text-gray-500 disabled:opacity-30 hover:bg-gray-200 transition-colors"
            >
              <ChevronRight size={22} />
            </button>
          </div>

          {/* 键盘提示 */}
          <div className="flex justify-center gap-4 text-[10px] text-gray-400">
            <span>← 认识</span>
            <span>空格 翻转</span>
            <span>不认识 →</span>
          </div>

          {/* 完成提示 */}
          {totalReviewed === words.length && words.length > 0 && (
            <div className="card bg-green-50 text-center py-4">
              <p className="text-green-700 font-medium">🎉 本轮已全部完成！</p>
              <p className="text-xs text-green-600 mt-1">
                认识 {totalKnown} 个 · 不认识 {totalUnknown} 个
              </p>
              <button
                onClick={resetProgress}
                className="mt-2 text-xs text-primary-500 hover:text-primary-700 font-medium"
              >
                再来一轮
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
