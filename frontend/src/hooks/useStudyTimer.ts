import { useState, useEffect, useRef, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const HEARTBEAT_INTERVAL = 30 // 秒

function getUserId(): string {
  return localStorage.getItem('edulingua_user_id') || 'default'
}

export function useStudyTimer(token: string | null) {
  const [todayMinutes, setTodayMinutes] = useState(0)
  const [isRunning, setIsRunning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const tabHiddenRef = useRef(false)
  const tokenRef = useRef(token)
  tokenRef.current = token

  const sendHeartbeat = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/progress/heartbeat?user_id=${encodeURIComponent(getUserId())}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokenRef.current}`,
        },
        body: JSON.stringify({ seconds: HEARTBEAT_INTERVAL }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data?.data?.today_minutes != null) {
          setTodayMinutes(data.data.today_minutes)
        }
      }
    } catch {
      // 网络故障静默忽略
    }
  }, [])

  // 页面可见性变化
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        tabHiddenRef.current = true
      } else if (tabHiddenRef.current && tokenRef.current) {
        tabHiddenRef.current = false
        sendHeartbeat()
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [sendHeartbeat])

  // 首次获取今日累计 + 主计时循环
  useEffect(() => {
    if (!token) {
      setIsRunning(false)
      setTodayMinutes(0)
      return
    }

    setIsRunning(true)

    // 首次加载：获取今日已有的累计分钟数（不发心跳，不加时间）
    const initFetch = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/progress/overview?user_id=${encodeURIComponent(getUserId())}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        })
        if (res.ok) {
          const data = await res.json()
          if (data?.data?.week_total_minutes != null) {
            // today 的 minutes 需要从 heatmap 或 aggregated data 获取
            // 简单方案：用 week_total_minutes 作为参考（非精确）
          }
        }
      } catch {}
    }
    initFetch()

    // 心跳定时器：每 30 秒累加
    intervalRef.current = setInterval(() => {
      if (!document.hidden) {
        sendHeartbeat()
      }
    }, HEARTBEAT_INTERVAL * 1000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setIsRunning(false)
    }
  }, [token, sendHeartbeat])

  return { todayMinutes, isRunning }
}
