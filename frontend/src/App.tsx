import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import DailyTasks from './pages/DailyTasks'
import ScenarioChat from './pages/ScenarioChat'
import Progress from './pages/Progress'
import Achievements from './pages/Achievements'
import Diagnosis from './pages/Diagnosis'
import Login from './pages/Login'
import BottomNav from './components/BottomNav'
import { useStudyTimer } from './hooks/useStudyTimer'
import { auth } from './api/client'

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('edulingua_token'))
  const { todayMinutes } = useStudyTimer(token)

  const handleLogin = (newToken: string, userId: string) => {
    setToken(newToken)
    localStorage.setItem('edulingua_token', newToken)
    localStorage.setItem('edulingua_user_id', userId)
  }

  const handleLogout = () => {
    setToken(null)
    localStorage.removeItem('edulingua_token')
    localStorage.removeItem('edulingua_user_id')
  }

  useEffect(() => {
    if (token) {
      localStorage.setItem('edulingua_token', token)
    } else {
      localStorage.removeItem('edulingua_token')
    }
  }, [token])

  // Token 自动校验：挂载时验证 token 有效性，过期则登出
  useEffect(() => {
    if (token) {
      auth.verify(token).catch(() => handleLogout())
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (!token) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="max-w-lg mx-auto min-h-screen pb-20">
      <Routes>
        <Route path="/" element={<Dashboard onLogout={handleLogout} todayMinutes={todayMinutes} />} />
        <Route path="/tasks" element={<DailyTasks />} />
        <Route path="/scenario" element={<ScenarioChat />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/achievements" element={<Achievements />} />
        <Route path="/diagnosis" element={<Diagnosis />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
    </div>
  )
}

export default App
