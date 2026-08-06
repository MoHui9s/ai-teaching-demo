// API 客户端 —— Tan同学-AI英语助教

const API_BASE = import.meta.env.VITE_API_BASE || ''

function getToken(): string | null {
  return localStorage.getItem('edulingua_token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

// Auth
export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user_id: string; email: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
}

// Tasks
export const tasks = {
  getDaily: (userId = 'default') =>
    request<{ success: boolean; data: any }>(`/api/tasks/daily?user_id=${userId}`),
  complete: (taskIndex: number, timeSpentMin: number, userId = 'default') =>
    request<{ success: boolean; data: any }>(`/api/tasks/daily/complete?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ task_index: taskIndex, time_spent_min: timeSpentMin }),
    }),
  getHistory: (days = 7, userId = 'default') =>
    request<{ success: boolean; data: any }>(`/api/tasks/history?user_id=${userId}&days=${days}`),
  diagnose: (data: { vocab_answers: string[]; pronunciation_text: string; listening_answers: string[] }, userId = 'default') =>
    request<{ level: string; vocab_estimate: number; message: string }>(`/api/tasks/diagnosis?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

// Chat (Agent)
export const chat = {
  send: (messages: { role: string; content: string }[], userId = 'default') =>
    request<{ choices: { message: { content: string } }[] }>('/v1/chat/completions', {
      method: 'POST',
      body: JSON.stringify({ messages, user_id: userId, model: 'tan-english-tutor' }),
    }),
}

// TTS
export const tts = {
  getAudio: (text: string, voice = 'en-US-AriaNeural', rate = '+0%') =>
    request<{ audio_url: string; cached: boolean; duration: number }>('/api/tts/audio', {
      method: 'POST',
      body: JSON.stringify({ text, voice, rate }),
    }),
}

// Scenarios
export const scenarios = {
  list: () =>
    request<{ success: boolean; data: { scenarios: any[] } }>('/api/scenarios/list'),
  getScene: (sceneId: string) =>
    request<{ success: boolean; data: any }>(`/api/scenarios/${sceneId}`),
  start: (sceneType: string, difficulty: string) =>
    request<{ success: boolean; data: any }>('/api/scenarios/start', {
      method: 'POST',
      body: JSON.stringify({ scene_type: sceneType, difficulty }),
    }),
}

// Progress
export const progress = {
  overview: (userId = 'default') =>
    request<{ success: boolean; data: any }>(`/api/progress/overview?user_id=${userId}`),
  weeklyReport: (weekStart?: string, userId = 'default') => {
    const params = new URLSearchParams({ user_id: userId })
    if (weekStart) params.set('week_start', weekStart)
    return request<{ success: boolean; data: any }>(`/api/progress/weekly-report?${params}`)
  },
  allReports: (userId = 'default') =>
    request<{ success: boolean; data: any }>(`/api/progress/reports?user_id=${userId}`),
}

// Achievements
export const achievements = {
  list: (userId = 'default') =>
    request<{ success: boolean; data: { achievements: any[]; total_unlocked: number; total_count: number } }>(`/api/achievements/list?user_id=${userId}`),
  check: (userId = 'default') =>
    request<{ success: boolean; data: { new_unlocks: any[] } }>(`/api/achievements/check?user_id=${userId}`, {
      method: 'POST',
    }),
}
