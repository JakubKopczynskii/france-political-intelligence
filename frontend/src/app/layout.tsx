import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'

export const metadata: Metadata = {
  title: 'France Political Intelligence',
  description: 'CAC 40 Portfolio Scenario Simulator — Local MVP',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full" style={{ background: '#090909', color: '#F5F5F5' }}>
        <div className="flex h-full min-h-screen">
          <Sidebar />
          <main className="flex-1 flex flex-col overflow-auto min-h-screen" style={{ background: '#090909' }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
