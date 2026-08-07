// API 客户端 —— Tan同学-AI英语助教

const API_BASE = import.meta.env.VITE_API_BASE || ''

function getToken(): string | null {
  return localStorage.getItem('edulingua_token')
}

function getUserId(): string {
  return localStorage.getItem('edulingua_user_id') || 'default'
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
  register: (email: string, password: string, name: string) =>
    request<{ access_token: string; user_id: string; email: string; name: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    }),
  verify: (token: string) =>
    request<{ user_id: string; email: string }>(`/api/auth/verify?token=${encodeURIComponent(token)}`, {
      method: 'POST',
    }),
}

// Tasks
export const tasks = {
  getDaily: (userId?: string) =>
    request<{ success: boolean; data: any }>(`/api/tasks/daily?user_id=${userId || getUserId()}`),
  complete: (taskIndex: number, timeSpentMin: number, userId?: string) =>
    request<{ success: boolean; data: any }>(`/api/tasks/daily/complete?user_id=${userId || getUserId()}`, {
      method: 'POST',
      body: JSON.stringify({ task_index: taskIndex, time_spent_min: timeSpentMin }),
    }),
  getHistory: (days = 7, userId?: string) =>
    request<{ success: boolean; data: any }>(`/api/tasks/history?user_id=${userId || getUserId()}&days=${days}`),
  diagnose: (data: { vocab_answers: string[]; pronunciation_text: string; listening_answers: string[] }, userId?: string) =>
    request<{ level: string; vocab_estimate: number; message: string }>(`/api/tasks/diagnosis?user_id=${userId || getUserId()}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  checkDictation: (userInput: string, referenceText: string) =>
    request<{ success: boolean; data: any }>('/api/tasks/dictation/check', {
      method: 'POST',
      body: JSON.stringify({ user_input: userInput, reference_text: referenceText }),
    }),
  assessPronunciation: async (audioBlob: Blob, referenceText: string) => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    formData.append('reference_text', referenceText)
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/api/tasks/pronunciation/assess`, {
      method: 'POST',
      body: formData,
      headers,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '评估失败' }))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
  },
}

// Chat (Agent)
export const chat = {
  send: (messages: { role: string; content: string }[]) =>
    request<{ choices: { message: { content: string } }[] }>('/v1/chat/completions', {
      method: 'POST',
      body: JSON.stringify({ messages, model: 'tan-english-tutor' }),
    }),
}

// TTS
export const tts = {
  getAudio: (text: string, voice = 'en-US-AriaNeural', rate = '+0%') =>
    request<{ audio_url: string; cached: boolean; duration: number }>('/api/tts/audio', {
      method: 'POST',
      body: JSON.stringify({ text, voice, rate }),
    }),
  getVoices: () =>
    request<{ voices: Record<string, { name: string; lang: string }> }>('/api/tts/voices'),
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
  overview: (userId?: string) =>
    request<{ success: boolean; data: any }>(`/api/progress/overview?user_id=${userId || getUserId()}`),
  weeklyReport: (weekStart?: string, userId?: string) => {
    const params = new URLSearchParams({ user_id: userId || getUserId() })
    if (weekStart) params.set('week_start', weekStart)
    return request<{ success: boolean; data: any }>(`/api/progress/weekly-report?${params}`)
  },
  allReports: (userId?: string) =>
    request<{ success: boolean; data: any }>(`/api/progress/reports?user_id=${userId || getUserId()}`),
}

// ASR (语音转文字)
export const asr = {
  transcribe: async (audioBlob: Blob, language = 'en') => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/api/asr/transcribe?language=${language}`, {
      method: 'POST',
      body: formData,
      headers,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'ASR 转写失败' }))
      throw new Error(err.detail || `ASR HTTP ${res.status}`)
    }
    return res.json()
  },
}

// Reading
export const reading = {
  list: (level = 'beginner') =>
    request<{ success: boolean; data: { articles: any[]; level: string } }>(`/api/reading/list?level=${level}`),
  getArticle: (articleId: string, level = 'beginner') =>
    request<{ success: boolean; data: any }>(`/api/reading/article/${articleId}?level=${level}`),
  checkAnswers: (articleId: string, answers: number[], level = 'beginner') =>
    request<{ success: boolean; data: { score: number; correct_count: number; total: number; results: any[] } }>(`/api/reading/check/${articleId}?level=${level}`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),
}

// Vocab
export const vocab = {
  list: (level = 'beginner', count = 20) =>
    request<{ success: boolean; data: { words: { word: string; chinese: string; example: string }[]; total_available: number; level: string } }>(`/api/vocab/list?level=${level}&count=${count}`),
}

// Achievements
export const achievements = {
  list: (userId?: string) =>
    request<{ success: boolean; data: { achievements: any[]; total_unlocked: number; total_count: number } }>(`/api/achievements/list?user_id=${userId || getUserId()}`),
  check: (userId?: string) =>
    request<{ success: boolean; data: { new_unlocks: any[] } }>(`/api/achievements/check?user_id=${userId || getUserId()}`, {
      method: 'POST',
    }),
}
