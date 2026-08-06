import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import DailyTasks from './pages/DailyTasks'
import Pronunciation from './pages/Pronunciation'
import ScenarioChat from './pages/ScenarioChat'
import Progress from './pages/Progress'
import Achievements from './pages/Achievements'
import Login from './pages/Login'
import BottomNav from './components/BottomNav'

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('edulingua_token'))

  useEffect(() => {
    if (token) {
      localStorage.setItem('edulingua_token', token)
    } else {
      localStorage.removeItem('edulingua_token')
    }
  }, [token])

  if (!token) {
    return <Login onLogin={setToken} />
  }

  return (
    <div className="max-w-lg mx-auto min-h-screen pb-20">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tasks" element={<DailyTasks />} />
        <Route path="/pronunciation" element={<Pronunciation />} />
        <Route path="/scenario" element={<ScenarioChat />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/achievements" element={<Achievements />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
    </div>
  )
}

export default App
