import { useEffect, useState } from 'react'
import { reading } from '../api/client'
import { ChevronLeft, CheckCircle, XCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import AudioPlayButton from '../components/AudioPlayButton'

interface Article {
  id: string
  title: string
  content: string
  questions: { question: string; options: string[] }[]
}

interface CheckResult {
  score: number
  correct_count: number
  total: number
  results: { question: string; your_answer: string; correct_answer: string; correct: boolean }[]
}

export default function Reading() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [level, setLevel] = useState('beginner')
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [userAnswers, setUserAnswers] = useState<number[]>([])
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadArticles(level)
  }, [level])

  const loadArticles = async (lvl: string) => {
    setLoading(true)
    setSelectedArticle(null)
    setCheckResult(null)
    try {
      const res = await reading.list(lvl)
      if (res?.data?.articles) setArticles(res.data.articles)
    } catch (e) {
      console.error('加载阅读材料失败', e)
    }
    setLoading(false)
  }

  const selectArticle = (article: Article) => {
    setSelectedArticle(article)
    setUserAnswers(new Array(article.questions.length).fill(-1))
    setCheckResult(null)
  }

  const handleSubmit = async () => {
    if (!selectedArticle) return
    try {
      const res = await reading.checkAnswers(selectedArticle.id, userAnswers, level)
      if (res?.data) setCheckResult(res.data)
    } catch (e) {
      console.error('检查答案失败', e)
    }
  }

  const levelLabels: Record<string, string> = {
    beginner: '初级', intermediate: '中级', advanced: '高级',
  }

  // 文章列表视图
  if (!selectedArticle) {
    return (
      <div className="p-5 space-y-5">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1.5 text-gray-400 hover:text-gray-600">
            <ChevronLeft size={20} />
          </button>
          <h1 className="page-title">阅读训练</h1>
        </div>

        <div className="flex gap-2">
          {Object.entries(levelLabels).map(([k, v]) => (
            <button
              key={k}
              onClick={() => setLevel(k)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                level === k ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {v}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded-2xl" />
            ))}
          </div>
        ) : articles.length === 0 ? (
          <div className="card text-center py-12 text-gray-500">
            <p>暂无阅读材料</p>
          </div>
        ) : (
          <div className="space-y-3">
            {articles.map((a, i) => (
              <button
                key={a.id}
                onClick={() => selectArticle(a)}
                className="card w-full text-left hover:bg-blue-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary-100 flex items-center justify-center text-primary-600 text-sm font-bold">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm truncate">{a.title}</h3>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                      {a.content.slice(0, 80)}...
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  // 文章阅读视图
  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => { setSelectedArticle(null); setCheckResult(null) }} className="p-1.5 text-gray-400 hover:text-gray-600">
          <ChevronLeft size={20} />
        </button>
        <h1 className="page-title text-lg">{selectedArticle.title}</h1>
      </div>

      {/* 文章内容 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <AudioPlayButton text={selectedArticle.content} size={16} />
          <span className="text-xs text-gray-400">朗读全文</span>
        </div>
        {selectedArticle.content.split('\n\n').map((para, i) => (
          <p key={i} className="text-sm leading-relaxed text-gray-700 mb-3 last:mb-0">
            {para.trim()}
          </p>
        ))}
      </div>

      {/* 题目 */}
      {!checkResult ? (
        <>
          <h3 className="font-semibold text-sm">阅读理解</h3>
          {selectedArticle.questions.map((q, qi) => (
            <div key={qi} className="card space-y-2">
              <p className="text-sm font-medium">
                {qi + 1}. {q.question}
              </p>
              <div className="space-y-2">
                {q.options.map((opt, oi) => (
                  <label
                    key={oi}
                    className={`flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-colors ${
                      userAnswers[qi] === oi
                        ? 'bg-primary-50 border border-primary-200'
                        : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                    }`}
                  >
                    <input
                      type="radio"
                      name={`q-${qi}`}
                      value={oi}
                      checked={userAnswers[qi] === oi}
                      onChange={() => {
                        const next = [...userAnswers]
                        next[qi] = oi
                        setUserAnswers(next)
                      }}
                      className="sr-only"
                    />
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      userAnswers[qi] === oi ? 'border-primary-500' : 'border-gray-300'
                    }`}>
                      {userAnswers[qi] === oi && (
                        <div className="w-2.5 h-2.5 rounded-full bg-primary-500" />
                      )}
                    </div>
                    <span className="text-sm">{opt}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}

          <button
            onClick={handleSubmit}
            disabled={userAnswers.some(a => a === -1)}
            className="w-full py-3 bg-primary-500 text-white rounded-xl font-medium disabled:opacity-50 hover:bg-primary-600 transition-colors"
          >
            提交答案
          </button>
        </>
      ) : (
        <>
          {/* 得分卡片 */}
          <div className={`card text-center py-4 ${
            checkResult.score >= 80 ? 'bg-green-50' : checkResult.score >= 50 ? 'bg-yellow-50' : 'bg-red-50'
          }`}>
            <p className="text-3xl font-bold mb-1">{checkResult.score} 分</p>
            <p className="text-sm text-gray-600">
              答对 {checkResult.correct_count}/{checkResult.total} 题
            </p>
          </div>

          {/* 逐题解析 */}
          <h3 className="font-semibold text-sm">答案解析</h3>
          {checkResult.results.map((r, i) => (
            <div key={i} className={`card border-l-4 ${r.correct ? 'border-l-green-500' : 'border-l-red-500'}`}>
              <div className="flex items-start gap-2 mb-2">
                {r.correct ? (
                  <CheckCircle size={16} className="text-green-500 mt-0.5 shrink-0" />
                ) : (
                  <XCircle size={16} className="text-red-500 mt-0.5 shrink-0" />
                )}
                <p className="text-sm font-medium">{i + 1}. {r.question}</p>
              </div>
              <div className="ml-6 space-y-1 text-xs">
                {!r.correct && (
                  <p className="text-red-600">你的答案: {r.your_answer}</p>
                )}
                <p className="text-green-600 font-medium">正确答案: {r.correct_answer}</p>
              </div>
            </div>
          ))}

          <button
            onClick={() => { setSelectedArticle(null); setCheckResult(null) }}
            className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors"
          >
            返回文章列表
          </button>
        </>
      )}
    </div>
  )
}
