'use client'

import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { api } from '@/lib/api'
import type { Event, HealthResponse, Portfolio, Scenario } from '@/lib/types'
import { Header } from '@/components/layout/Header'

function Spinner() {
  return (
    <div
      className="sys-spin"
      style={{
        width: 14,
        height: 14,
        borderRadius: '50%',
        border: '1px solid #262626',
        borderTopColor: '#929292',
      }}
    />
  )
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      className="flex items-center justify-between py-3"
      style={{ borderBottom: '1px solid #262626' }}
    >
      <span className="font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>
        {label}
      </span>
      <span className="font-mono text-[13px] font-medium" style={{ color: '#F5F5F5' }}>
        {value}
      </span>
    </div>
  )
}

export default function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.health().catch(() => null),
      api.getScenarios().catch(() => [] as Scenario[]),
      api.getEvents({ limit: 5 }).catch(() => [] as Event[]),
      api.getDemoPortfolio().catch(() => null),
    ])
      .then(([h, s, e, p]) => {
        setHealth(h)
        setScenarios(s)
        setEvents(e)
        setPortfolio(p)
        setError(null)
      })
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  const connected = health !== null
  const probSum = scenarios.reduce((acc, s) => acc + s.probability, 0)

  const sectorData = portfolio?.holdings.reduce<Record<string, number>>(
    (acc, h) => {
      const sec = h.sector ?? 'Unknown'
      acc[sec] = (acc[sec] ?? 0) + h.weight
      return acc
    },
    {}
  ) ?? {}

  const sectorChart = Object.entries(sectorData)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 7)
    .map(([sector, weight]) => ({ sector, weight: Math.round(weight * 100) }))

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Overview"
        lastRefresh={health?.last_refresh}
        isConnected={connected}
        showDemoLabel={health?.demo_mode ?? true}
      />

      <div className="flex-1 p-6 overflow-auto">
        {error && (
          <div
            className="mb-6 px-4 py-3 font-mono text-[11px]"
            style={{ color: '#FF3B30', border: '1px solid #2a1a1a', borderRadius: '2px' }}
          >
            BACKEND ERROR — {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
            <Spinner />
            <span className="font-mono text-[11px] tracking-widest uppercase">SCANNING</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left column */}
            <div className="lg:col-span-1">
              <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                SYSTEM STATUS
              </div>
              <div>
                <StatRow label="ARTICLES" value={health?.article_count ?? 0} />
                <StatRow label="EVENTS" value={health?.event_count ?? 0} />
                <StatRow label="SCENARIOS" value={scenarios.length} />
                <StatRow
                  label="PORTFOLIO"
                  value={portfolio ? `€${(portfolio.total_value / 1000).toFixed(0)}k` : '—'}
                />
                <StatRow label="HOLDINGS" value={portfolio?.holdings.length ?? 0} />
              </div>

              {scenarios.length > 0 && Math.abs(probSum - 1) > 0.01 && (
                <div
                  className="mt-4 px-3 py-2 font-mono text-[10px]"
                  style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}
                >
                  PROB SUM = {(probSum * 100).toFixed(1)}% — MUST BE 100%
                </div>
              )}

              <div className="mt-8">
                <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                  POLITICAL SCENARIOS
                </div>
                {scenarios.map((s) => (
                  <div
                    key={s.id}
                    className="py-3 flex items-baseline justify-between"
                    style={{ borderBottom: '1px solid #262626' }}
                  >
                    <span className="text-[12px]" style={{ color: '#929292' }}>
                      {s.display_name}
                    </span>
                    <span className="font-mono text-[13px] font-medium" style={{ color: '#F5F5F5' }}>
                      {(s.probability * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
                {scenarios.length > 0 && (
                  <div className="pt-2">
                    <span className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>
                      ILLUSTRATIVE ANALYST INPUT
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Right columns */}
            <div className="lg:col-span-2 flex flex-col gap-8">
              {/* Sector exposure */}
              <div>
                <div className="font-mono text-[10px] tracking-widest uppercase mb-4" style={{ color: '#606060' }}>
                  PORTFOLIO SECTOR EXPOSURE
                </div>
                {sectorChart.length === 0 ? (
                  <div className="font-mono text-[11px] py-4" style={{ color: '#3a3a3a' }}>
                    NO PORTFOLIO LOADED
                  </div>
                ) : (
                  <div style={{ height: 160 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sectorChart} layout="vertical" margin={{ left: 0, right: 8 }}>
                        <XAxis
                          type="number"
                          tick={{ fill: '#606060', fontSize: 10, fontFamily: 'Geist Mono' }}
                          unit="%"
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="sector"
                          tick={{ fill: '#929292', fontSize: 10, fontFamily: 'Geist Mono' }}
                          width={110}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          contentStyle={{
                            background: '#101010',
                            border: '1px solid #262626',
                            borderRadius: 2,
                            fontSize: 11,
                            fontFamily: 'Geist Mono',
                            color: '#F5F5F5',
                          }}
                          cursor={{ fill: '#151515' }}
                          formatter={(v: unknown) => [`${v as number}%`, 'WEIGHT']}
                        />
                        <Bar dataKey="weight" radius={0} maxBarSize={8}>
                          {sectorChart.map((_, i) => (
                            <Cell
                              key={i}
                              fill={i === 0 ? '#F5F5F5' : '#262626'}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Latest events */}
              <div>
                <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                  LATEST EVENTS
                </div>
                {events.length === 0 ? (
                  <div className="font-mono text-[11px] py-4" style={{ color: '#3a3a3a' }}>
                    NO EVENTS — REFRESH FEEDS
                  </div>
                ) : (
                  <div>
                    {events.slice(0, 5).map((e) => (
                      <div
                        key={e.id}
                        className="py-3"
                        style={{ borderBottom: '1px solid #262626' }}
                      >
                        <div className="text-[13px]" style={{ color: '#F5F5F5' }}>
                          {e.headline}
                        </div>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="font-mono text-[10px]" style={{ color: '#606060' }}>
                            {e.source_name}
                          </span>
                          {e.is_synthetic && (
                            <span className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>
                              SYNTHETIC
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
