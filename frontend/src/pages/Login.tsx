import { useState } from 'react'
import { auth } from '../api/client'

interface LoginProps {
  onLogin: (token: string) => void
}

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState('user@example.com')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await auth.login(email, password)
      onLogin(res.access_token)
    } catch (err: any) {
      setError(err.message || '登录失败')
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

        <form onSubmit={handleLogin} className="card space-y-4">
          <h2 className="text-lg font-semibold text-center">登录</h2>
          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3">{error}</div>
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
              placeholder="password123"
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? '登录中...' : '开始学习'}
          </button>
          <p className="text-xs text-gray-400 text-center">
            开发模式：使用默认账号即可登录
          </p>
        </form>
      </div>
    </div>
  )
}
