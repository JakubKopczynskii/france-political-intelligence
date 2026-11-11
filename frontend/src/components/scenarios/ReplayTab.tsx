'use client'

import { useEffect, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import type { Episode } from '@/lib/types'

type Companies = Record<string, { name: string; sector: string; weight: number }>

function signed(v: number | null | undefined, digits = 1) {
  return v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
}

function color(v: number) {
  if (v >= 2) return '#34C759'
  if (v >= 0) return '#929292'
  if (v >= -3) return '#FF9500'
  return '#FF3B30'
}

function bg(v: number) {
  if (v >= 3) return 'rgba(52,199,89,0.22)'
  if (v >= 1) return 'rgba(52,199,89,0.1)'
  if (v >= -1) return '#101010'
  if (v >= -3) return 'rgba(255,149,0,0.12)'
  if (v >= -7) return 'rgba(255,59,48,0.16)'
  return 'rgba(255,59,48,0.3)'
}

export function ReplayTab() {
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [companies, setCompanies] = useState<Companies>({})
  const [message, setMessage] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [adjusted, setAdjusted] = useState(false)

  useEffect(() => {
    api.getEpisodes()
      .then((r) => {
        if (!r.available) {
          setMessage(r.message ?? 'Not available')
          return
        }
        setEpisodes(r.episodes)
        setCompanies(r.companies ?? {})
        setSelectedId(r.episodes.find((e) => e.id === '2024_dissolution')?.id ?? r.episodes[0]?.id ?? null)
      })
      .catch((e: unknown) => setMessage(String(e)))
  }, [])

  const ep = episodes.find((e) => e.id === selectedId)
  const rows = useMemo(() => {
    if (!ep) return []
    return Object.entries(ep.stocks)
      .map(([t, r]) => ({ ticker: t, value: adjusted ? r.abnormal_pct : r.raw_pct, ...companies[t] }))
      .filter((r) => r.name)
      .sort((a, b) => b.weight - a.weight)
  }, [ep, adjusted, companies])

  const sectors = useMemo(() => {
    const acc: Record<string, { w: number; v: number }> = {}
    rows.forEach((r) => {
      acc[r.sector] ??= { w: 0, v: 0 }
      acc[r.sector].w += r.weight
      acc[r.sector].v += r.weight * r.value
    })
    return Object.entries(acc).map(([s, { w, v }]) => ({ sector: s, value: v / w })).sort((a, b) => a.value - b.value)
  }, [rows])

  if (message) return <div className="font-mono text-[11px] py-8" style={{ color: '#606060' }}>{message}</div>
  if (!ep) return null

  const totalWeight = rows.reduce((s, r) => s + r.weight, 0)
  const sorted = [...rows].sort((a, b) => a.value - b.value)

  return (
    <div>
      <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
        HOW THE CAC40 ACTUALLY MOVED IN REAL FRENCH POLITICAL SHOCKS. THESE EPISODES CALIBRATE THE HISTORICAL-ANALOG IMPACTS.
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        <div className="flex flex-col gap-1">
          {episodes.map((e) => (
            <button
              key={e.id}
              onClick={() => setSelectedId(e.id)}
              className="text-left p-3"
              style={{ background: e.id === selectedId ? '#151515' : 'transparent', border: `1px solid ${e.id === selectedId ? '#606060' : '#1a1a1a'}` }}
            >
              <div className="text-[12px]" style={{ color: '#F5F5F5' }}>{e.label}</div>
              <div className="flex gap-3 font-mono text-[10px] mt-1">
                <span style={{ color: '#606060' }}>CAC <span style={{ color: color(e.cac_pct ?? 0) }}>{signed(e.cac_pct)}</span></span>
                <span style={{ color: '#606060' }}>DAX <span style={{ color: color(e.dax_pct) }}>{signed(e.dax_pct)}</span></span>
              </div>
            </button>
          ))}
        </div>

        <div className="min-w-0">
          <div className="p-4 mb-3" style={{ background: '#101010', border: '1px solid #262626' }}>
            <div className="flex flex-wrap items-start gap-4 justify-between">
              <div className="min-w-0 flex-1">
                <div className="text-[15px]" style={{ color: '#F5F5F5' }}>{ep.label}</div>
                <div className="font-mono text-[10px] mt-0.5" style={{ color: '#606060' }}>Close {ep.trading_start} → close {ep.trading_end}</div>
                <div className="text-[12px] mt-2" style={{ color: '#929292' }}>{ep.description}</div>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-[11px]">
                <span style={{ color: '#606060' }}>CAC40</span><span style={{ color: color(ep.cac_pct ?? 0) }}>{signed(ep.cac_pct)}</span>
                <span style={{ color: '#606060' }}>DAX</span><span style={{ color: color(ep.dax_pct) }}>{signed(ep.dax_pct)}</span>
                <span style={{ color: '#606060' }}>CAC VS DAX (β-ADJ)</span><span style={{ color: color(ep.index_abnormal_pct ?? 0) }}>{signed(ep.index_abnormal_pct)}</span>
                <span style={{ color: '#606060' }}>EU BANKS</span><span style={{ color: color(ep.eu_banks_pct ?? 0) }}>{signed(ep.eu_banks_pct)}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 mb-2">
            {[false, true].map((adj) => (
              <button
                key={String(adj)}
                onClick={() => setAdjusted(adj)}
                className="font-mono text-[10px] tracking-widest px-3 py-1.5"
                style={{ background: adjusted === adj ? '#1a1a1a' : 'transparent', border: '1px solid #262626', color: adjusted === adj ? '#F5F5F5' : '#606060' }}
              >
                {adj ? 'FRANCE-SPECIFIC (VS DAX)' : 'ACTUAL MOVE'}
              </button>
            ))}
            <span className="font-mono text-[9px] ml-2" style={{ color: '#3a3a3a' }}>TILE SIZE = CAC40 WEIGHT</span>
          </div>

          <div className="flex flex-wrap gap-0.5 mb-4">
            {rows.map((r) => {
              const w = Math.max(52, Math.round((r.weight / totalWeight) * 1100))
              return (
                <div key={r.ticker} title={`${r.name}: ${signed(r.value, 2)}`} style={{ width: w, height: 50, background: bg(r.value), border: '1px solid #1a1a1a', padding: '4px 6px' }}>
                  <div className="font-mono text-[10px]" style={{ color: '#F5F5F5' }}>{r.ticker.replace(/\.(PA|MI|AS)$/, '')}</div>
                  <div className="font-mono text-[11px] tabular-nums" style={{ color: color(r.value) }}>{signed(r.value)}</div>
                </div>
              )
            })}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[{ title: 'HIT HARDEST', list: sorted.slice(0, 6) }, { title: 'HELD UP BEST', list: sorted.slice(-6).reverse() }].map(({ title, list }) => (
              <div key={title} className="p-3" style={{ border: '1px solid #1a1a1a' }}>
                <div className="font-mono text-[9px] tracking-widest mb-2" style={{ color: '#606060' }}>{title}</div>
                {list.map((r) => (
                  <div key={r.ticker} className="flex justify-between text-[11px] py-0.5">
                    <span style={{ color: '#929292' }}>{r.name}</span>
                    <span className="font-mono" style={{ color: color(r.value) }}>{signed(r.value)}</span>
                  </div>
                ))}
              </div>
            ))}
            <div className="p-3" style={{ border: '1px solid #1a1a1a' }}>
              <div className="font-mono text-[9px] tracking-widest mb-2" style={{ color: '#606060' }}>BY SECTOR (WEIGHTED)</div>
              {sectors.map((s) => (
                <div key={s.sector} className="flex justify-between text-[11px] py-0.5">
                  <span style={{ color: '#929292' }}>{s.sector}</span>
                  <span className="font-mono" style={{ color: color(s.value) }}>{signed(s.value)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="font-mono text-[9px] mt-3" style={{ color: '#3a3a3a' }}>
            Prices: Yahoo Finance, adjusted closes. France-specific = stock return minus β × DAX return, β from the 250 trading days before the episode.
          </div>
        </div>
      </div>
    </div>
  )
}
