import { useNavigate } from 'react-router-dom'
import { Sparkles, Target, Mic } from 'lucide-react'

interface OnboardingGuideProps {
  onStartDiagnosis: () => void
}

export default function OnboardingGuide({ onStartDiagnosis }: OnboardingGuideProps) {
  const navigate = useNavigate()

  const steps = [
    {
      icon: <Target size={22} className="text-primary-500" />,
      title: '能力诊断',
      desc: '5分钟快速测试，了解你的英语水平',
      action: onStartDiagnosis,
      label: '开始诊断',
    },
    {
      icon: <Sparkles size={22} className="text-green-500" />,
      title: '每日任务',
      desc: '基于你的水平，AI 生成今日三件事',
      action: () => navigate('/tasks'),
      label: '查看任务',
    },
    {
      icon: <Mic size={22} className="text-purple-500" />,
      title: '场景对话',
      desc: '10+ 真实场景，AI 陪你练口语',
      action: () => navigate('/scenario'),
      label: '去对话',
    },
  ]

  return (
    <div className="card bg-gradient-to-br from-primary-50 via-white to-accent-50 border-2 border-primary-100">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">👋</span>
        <div>
          <h3 className="font-bold text-primary-700">欢迎加入 Tan同学！</h3>
          <p className="text-sm text-gray-500">让我们用 3 步开启你的英语学习之旅</p>
        </div>
      </div>
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div
            key={i}
            className="flex items-center gap-3 p-3 bg-white rounded-xl hover:shadow-sm transition-shadow cursor-pointer"
            onClick={step.action}
          >
            <div className="w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center flex-shrink-0">
              {step.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm">{step.title}</div>
              <div className="text-xs text-gray-500">{step.desc}</div>
            </div>
            <button
              className="btn-primary text-xs px-3 py-1.5 rounded-lg flex-shrink-0"
              onClick={(e) => { e.stopPropagation(); step.action() }}
            >
              {step.label}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
