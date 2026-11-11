'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  Newspaper,
  Flag,
  BarChart2,
  Briefcase,
  Zap,
  Landmark,
  Settings,
} from 'lucide-react'

const NAV = [
  { href: '/', label: 'Overview', icon: Home },
  { href: '/news', label: 'News Intel', icon: Newspaper },
  { href: '/scenarios', label: 'Scenarios', icon: Flag },
  { href: '/companies', label: 'CAC 40', icon: BarChart2 },
  { href: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { href: '/stress-test', label: 'Stress Test', icon: Zap },
  { href: '/ecb', label: 'ECB', icon: Landmark },
  { href: '/methodology', label: 'Methodology', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside
      className="flex flex-col flex-shrink-0 min-h-screen"
      style={{
        width: '200px',
        background: '#090909',
        borderRight: '1px solid #262626',
      }}
    >
      {/* System header */}
      <div className="px-4 py-4" style={{ borderBottom: '1px solid #262626' }}>
        <div
          className="font-mono text-[10px] tracking-widest uppercase mb-1"
          style={{ color: '#606060' }}
        >
          {'// SYS'}
        </div>
        <div className="text-[13px] font-medium" style={{ color: '#F5F5F5' }}>
          FR Political Intel
        </div>
        <div
          className="font-mono text-[10px] mt-0.5"
          style={{ color: '#606060' }}
        >
          CAC40 · v0.1.0
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-col py-2 flex-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href || (href !== '/' && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-4 py-2 text-[13px] transition-colors relative"
              style={{
                color: active ? '#F5F5F5' : '#606060',
                borderLeft: active ? '2px solid #F5F5F5' : '2px solid transparent',
                paddingLeft: '14px',
              }}
            >
              <Icon
                className="flex-shrink-0"
                size={14}
                style={{ color: active ? '#F5F5F5' : '#606060' }}
              />
              <span
                className="font-mono text-[11px] tracking-wide uppercase"
                style={{ color: active ? '#F5F5F5' : '#606060' }}
              >
                {label}
              </span>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3" style={{ borderTop: '1px solid #262626' }}>
        <div className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>
          LOCAL · PRIVATE
        </div>
      </div>
    </aside>
  )
}
