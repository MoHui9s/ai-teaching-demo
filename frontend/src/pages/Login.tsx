import { useState } from 'react'
import { auth } from '../api/client'

interface LoginProps {
  onLogin: (token: string, userId: string) => void
}

export default function Login({ onLogin }: LoginProps) {
  const [isRegister, setIsRegister] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('user@example.com')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isRegister) {
        const res = await auth.register(email, password, name)
        onLogin(res.access_token, res.user_id)
      } else {
        const res = await auth.login(email, password)
        onLogin(res.access_token, res.user_id)
      }
    } catch (err: any) {
      setError(err.message || (isRegister ? '注册失败' : '登录失败'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-accent-600 p-5">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">📚</div>
          <h1 className="text-3xl font-bold text-white mb-2">Tan同学-AI英语助教</h1>
          <p className="text-white/70 text-sm">AI驱动的全栈英语学习系统</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          {/* 登录/注册切换 */}
          <div className="flex bg-gray-100 rounded-xl p-1">
            <button
              type="button"
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                !isRegister ? 'bg-white shadow text-primary-600' : 'text-gray-500'
              }`}
              onClick={() => { setIsRegister(false); setError('') }}
            >
              登录
            </button>
            <button
              type="button"
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                isRegister ? 'bg-white shadow text-primary-600' : 'text-gray-500'
              }`}
              onClick={() => { setIsRegister(true); setError('') }}
            >
              注册
            </button>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3">{error}</div>
          )}

          {/* 注册时显示姓名 */}
          {isRegister && (
            <div>
              <label className="text-sm text-gray-600 mb-1 block">姓名</label>
              <input
                type="text"
                className="input-field"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="你的名字"
              />
            </div>
          )}

          <div>
            <label className="text-sm text-gray-600 mb-1 block">邮箱</label>
            <input
              type="email"
              className="input-field"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
            />
          </div>
          <div>
            <label className="text-sm text-gray-600 mb-1 block">密码</label>
            <input
              type="password"
              className="input-field"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={isRegister ? '至少6位密码' : 'password123'}
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? (isRegister ? '注册中...' : '登录中...') : (isRegister ? '创建账号' : '开始学习')}
          </button>
          <p className="text-xs text-gray-400 text-center">
            {isRegister ? '已有账号？上方切换到登录' : '开发模式：使用默认账号即可登录'}
          </p>
        </form>
      </div>
    </div>
  )
}
