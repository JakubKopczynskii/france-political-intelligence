'use client'

import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '@/lib/api'
import type { ElectionHistory } from '@/lib/types'

const SCENARIOS: Record<string, { label: string; color: string }> = {
  centrist: { label: 'Centrist', color: '#D9A441' },
  national_rally: { label: 'National Rally', color: '#4C7BD9' },
  left_wing: { label: 'Left Wing', color: '#D9488B' },
  hung_parliament: { label: 'Hung Parliament', color: '#929292' },
}
const COLORS = ['#4C7BD9', '#D9488B', '#D9A441', '#8B6DD9', '#5FB8A6', '#E07A3F', '#9AA5B1', '#C2C25A']

const axis = { fill: '#606060', fontSize: 9, fontFamily: 'monospace' }
const tooltip = { contentStyle: { background: '#101010', border: '1px solid #262626', fontSize: 11, fontFamily: 'monospace' }, labelStyle: { color: '#929292' } }

function Chart({ title, data, keys, colors, unit, note }: {
  title: string
  data: Record<string, string | number | null>[]
  keys: string[]
  colors: Record<string, string>
  unit: string
  note?: string
}) {
  return (
    <div className="p-4 mb-4" style={{ background: '#101010', border: '1px solid #262626' }}>
      <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>{title}</div>
      {data.length < 2 ? (
        <div className="font-mono text-[11px] py-6" style={{ color: '#606060' }}>
          {data.length === 1 ? 'First data point recorded today — the chart fills in as the daily job runs.' : 'No data recorded yet.'}
        </div>
      ) : (
        <div style={{ height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="#1a1a1a" vertical={false} />
              <XAxis dataKey="date" tick={axis} stroke="#262626" tickFormatter={(d: string) => d.slice(2, 10)} minTickGap={30} />
              <YAxis tick={axis} stroke="#262626" unit={unit} />
              <Tooltip {...tooltip} />
              <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'monospace' }} />
              {keys.map((k) => (
                <Line key={k} type="monotone" dataKey={k} stroke={colors[k]} dot={data.length < 15} strokeWidth={1.5} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {note && <div className="font-mono text-[9px] mt-2" style={{ color: '#3a3a3a' }}>{note}</div>}
    </div>
  )
}

export function HistoryTab() {
  const [hist, setHist] = useState<ElectionHistory | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getElectionHistory().then(setHist).catch((e: unknown) => setError(String(e)))
  }, [])

  const scenarioData = useMemo(() => {
    if (!hist) return []
    const points = new Map<string, Record<string, number | string>>()
    const toRow = (date: string, probs: Record<string, number>) => {
      const row: Record<string, number | string> = { date }
      Object.entries(SCENARIOS).forEach(([slug, { label }]) => {
        if (probs[slug] != null) row[label] = Math.round(probs[slug] * 1000) / 10
      })
      return row
    }
    // Replay audit revisions into a running state so pre-snapshot history is visible too
    const state: Record<string, number> = {}
    hist.revisions.forEach((r) => {
      if (!r.date || !r.scenario) return
      if (state[r.scenario] == null) state[r.scenario] = r.old
      state[r.scenario] = r.new
      if (Object.keys(state).length === 4) points.set(r.date.slice(0, 10), toRow(r.date.slice(0, 10), { ...state }))
    })
    hist.scenario_snapshots.forEach((s) => points.set(s.date, toRow(s.date, s.probabilities)))
    return Array.from(points.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)))
  }, [hist])

  const presData = useMemo(() => {
    if (!hist) return { rows: [], keys: [] as string[] }
    const totals: Record<string, number> = {}
    hist.presidential_snapshots.forEach((s) => Object.entries(s.p_win).forEach(([k, v]) => { totals[k] = Math.max(totals[k] ?? 0, v) }))
    const keys = Object.keys(totals).sort((a, b) => totals[b] - totals[a]).slice(0, 6)
    const rows = hist.presidential_snapshots.map((s) => {
      const row: Record<string, string | number | null> = { date: s.date }
      keys.forEach((k) => { row[k] = s.p_win[k] != null ? Math.round(s.p_win[k] * 1000) / 10 : 0 })
      return row
    })
    return { rows, keys }
  }, [hist])

  const pollData = useMemo(() => {
    const ph = hist?.poll_history
    if (!ph) return { rows: [], keys: [] as string[] }
    const keys = Object.keys(ph.series).map((k) => ph.names[k] ?? k)
    const rows = ph.dates.map((d, i) => {
      const row: Record<string, string | number | null> = { date: d }
      Object.keys(ph.series).forEach((k) => { row[ph.names[k] ?? k] = ph.series[k][i] })
      return row
    })
    return { rows, keys }
  }, [hist])

  if (error) return <div className="font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>{error}</div>
  if (!hist) return <div className="font-mono text-[11px] py-8" style={{ color: '#606060' }}>LOADING</div>

  const scenarioColors = Object.fromEntries(Object.values(SCENARIOS).map((s) => [s.label, s.color]))
  const idx = (keys: string[]) => Object.fromEntries(keys.map((k, i) => [k, COLORS[i % COLORS.length]]))

  return (
    <div>
      <Chart
        title="Scenario probabilities over time"
        data={scenarioData}
        keys={Object.values(SCENARIOS).map((s) => s.label)}
        colors={scenarioColors}
        unit="%"
        note="Daily snapshot of the blended probabilities, plus earlier audit-log revisions. The fixed analyst prior is not included in this line."
      />
      <Chart
        title="Presidential win probability over time"
        data={presData.rows}
        keys={presData.keys}
        colors={idx(presData.keys)}
        unit="%"
        note="One snapshot per day from the two-round poll simulation."
      />
      <Chart
        title="First-round polls since 2025 — 30-day rolling average"
        data={pollData.rows}
        keys={pollData.keys}
        colors={idx(pollData.keys)}
        unit="%"
        note="Rebuilt from every poll on the Wikipedia list, so this history is complete from day one."
      />
      {hist.revisions.length > 0 && (
        <div className="p-4" style={{ background: '#101010', border: '1px solid #262626' }}>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>PROBABILITY AUDIT LOG (LATEST 15)</div>
          {[...hist.revisions].reverse().slice(0, 15).map((r, i) => (
            <div key={i} className="flex gap-3 py-1 font-mono text-[10px]" style={{ borderBottom: '1px solid #1a1a1a' }}>
              <span className="w-24 flex-shrink-0" style={{ color: '#606060' }}>{r.date?.slice(0, 10)}</span>
              <span className="w-32 flex-shrink-0" style={{ color: '#929292' }}>{SCENARIOS[r.scenario]?.label ?? r.scenario}</span>
              <span className="w-28 flex-shrink-0" style={{ color: '#F5F5F5' }}>{(r.old * 100).toFixed(1)}% → {(r.new * 100).toFixed(1)}%</span>
              <span className="truncate" style={{ color: '#3a3a3a' }}>{r.rationale}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
