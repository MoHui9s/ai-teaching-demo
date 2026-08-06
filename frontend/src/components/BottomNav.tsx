import { NavLink, useLocation } from 'react-router-dom'
import { Home, CheckSquare, MessageCircle, BarChart3 } from 'lucide-react'

const navItems = [
  { to: '/', icon: Home, label: '看板' },
  { to: '/tasks', icon: CheckSquare, label: '任务' },
  { to: '/scenario', icon: MessageCircle, label: '对话' },
  { to: '/progress', icon: BarChart3, label: '进度' },
]

export default function BottomNav() {
  const location = useLocation()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 z-50">
      <div className="max-w-lg mx-auto flex justify-around py-2">
        {navItems.map(({ to, icon: Icon, label }) => {
          const active = location.pathname === to
          return (
            <NavLink
              key={to}
              to={to}
              className={`flex flex-col items-center gap-1 px-3 py-1 rounded-xl transition-colors ${
                active ? 'text-primary-600' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              <Icon size={22} />
              <span className="text-xs font-medium">{label}</span>
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
