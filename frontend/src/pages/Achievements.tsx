import { useEffect, useState } from 'react'
import { achievements } from '../api/client'
import { Trophy, Lock } from 'lucide-react'

export default function Achievements() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAchievements()
  }, [])

  const loadAchievements = async () => {
    setLoading(true)
    try {
      const res = await achievements.list()
      if (res?.data) setData(res.data)
    } catch (e) {
      console.error('加载成就失败', e)
    }
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="p-5 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/3" />
        <div className="grid grid-cols-2 gap-3">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-24 bg-gray-200 rounded-2xl" />
          ))}
        </div>
      </div>
    )
  }

  const list = data?.achievements || []
  const unlocked = data?.total_unlocked || 0
  const total = data?.total_count || 0

  const handleCheck = async () => {
    try {
      const res = await achievements.check()
      if (res?.data?.new_unlocks?.length > 0) {
        loadAchievements()
      } else {
        alert('暂无新成就解锁')
      }
    } catch (e) {
      console.error('检查成就失败', e)
    }
  }

  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">成就徽章</h1>
          <p className="page-subtitle">解锁 {unlocked}/{total}</p>
        </div>
        <button onClick={handleCheck} className="btn-secondary text-sm">
          刷新
        </button>
      </div>

      {/* 进度条 */}
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-yellow-500 rounded-full transition-all"
          style={{ width: `${total > 0 ? (unlocked / total) * 100 : 0}%` }}
        />
      </div>

      {/* 成就网格 */}
      <div className="grid grid-cols-2 gap-3">
        {list.map((achievement: any, i: number) => (
          <div
            key={i}
            className={`card text-center ${achievement.unlocked ? '' : 'opacity-50'}`}
          >
            <div className="text-3xl mb-2">
              {achievement.unlocked ? '🏆' : <Lock size={28} className="mx-auto text-gray-300" />}
            </div>
            <h3 className="font-semibold text-sm">{achievement.name}</h3>
            <p className="text-xs text-gray-500 mt-1">{achievement.description}</p>
            {achievement.progress && !achievement.unlocked && (
              <div className="mt-2">
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full"
                    style={{
                      width: `${Math.min(
                        100,
                        (achievement.progress.current / achievement.progress.target) * 100
                      )}%`
                    }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {achievement.progress.current}/{achievement.progress.target}
                </p>
              </div>
            )}
            {achievement.unlocked && achievement.unlocked_at && (
              <p className="text-xs text-green-500 mt-1">
                {new Date(achievement.unlocked_at).toLocaleDateString('zh-CN')}
              </p>
            )}
          </div>
        ))}
      </div>

      {list.length === 0 && (
        <div className="card text-center py-12">
          <Trophy size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">开始学习，解锁你的第一个成就！</p>
        </div>
      )}
    </div>
  )
}
