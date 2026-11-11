'use client'

import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '@/lib/api'
import type { Bloc, CalendarEvent, ImpactMethod, MarketRisk, Presidential, RiskComponent } from '@/lib/types'
import { Header } from '@/components/layout/Header'

const BLOC_COLORS: Record<Bloc, string> = {
  far_right: '#4C7BD9',
  centre_right: '#D9A441',
  left: '#D9488B',
  other: '#606060',
}

const SERIES_COLORS = ['#4C7BD9', '#D9488B', '#D9A441', '#8B6DD9', '#5FB8A6', '#E07A3F', '#9AA5B1', '#C2C25A']

function pct(v: number | null | undefined, digits = 0) {
  return v == null ? '—' : `${(v * 100).toFixed(digits)}%`
}

function signed(v: number | null | undefined, digits = 1) {
  return v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
}

function impactColor(v: number | null | undefined) {
  if (v == null) return '#606060'
  if (v >= 1) return '#34C759'
  if (v >= -1) return '#929292'
  if (v >= -5) return '#FF9500'
  return '#FF3B30'
}

function daysUntil(iso: string) {
  const ms = new Date(iso + 'T00:00:00').getTime() - new Date(new Date().toDateString()).getTime()
  return Math.round(ms / 86400000)
}

function SectionLabel({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
      <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>{children}</div>
      {right}
    </div>
  )
}

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`p-4 ${className}`} style={{ background: '#101010', border: '1px solid #262626' }}>
      {children}
    </div>
  )
}

function Bar({ value, color, max = 1 }: { value: number; color: string; max?: number }) {
  return (
    <div style={{ flex: 1, height: 6, background: '#1a1a1a', minWidth: 40 }}>
      <div style={{ width: `${Math.min(value / max, 1) * 100}%`, height: '100%', background: color }} />
    </div>
  )
}

function Countdown({ pres }: { pres: Presidential }) {
  const items = [
    { label: 'FIRST ROUND', date: pres.first_round_date },
    { label: 'SECOND ROUND', date: pres.second_round_date },
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      {items.map((it) => (
        <Panel key={it.label}>
          <div className="font-mono text-[9px] tracking-widest mb-1" style={{ color: '#606060' }}>{it.label}</div>
          <div className="font-mono text-[22px] tabular-nums" style={{ color: '#F5F5F5' }}>{daysUntil(it.date)}<span className="text-[11px] ml-1" style={{ color: '#606060' }}>days</span></div>
          <div className="font-mono text-[10px]" style={{ color: '#929292' }}>
            {new Date(it.date).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
        </Panel>
      ))}
      <Panel>
        <div className="font-mono text-[9px] tracking-widest mb-1" style={{ color: '#606060' }}>POLLS IN WINDOW</div>
        <div className="font-mono text-[22px] tabular-nums" style={{ color: '#F5F5F5' }}>{pres.window.n_polls}</div>
        <div className="font-mono text-[10px]" style={{ color: '#929292' }}>{pres.window.from} → {pres.window.to} · {pres.window.n_hypotheses} line-ups</div>
      </Panel>
      <Panel>
        <div className="font-mono text-[9px] tracking-widest mb-1" style={{ color: '#606060' }}>SIMULATIONS</div>
        <div className="font-mono text-[22px] tabular-nums" style={{ color: '#F5F5F5' }}>{pres.n_sims.toLocaleString('en-GB')}</div>
        <div className="font-mono text-[10px]" style={{ color: '#929292' }}>updated {new Date(pres.computed_at).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })}</div>
      </Panel>
    </div>
  )
}

function BlocOverview({ pres, method }: { pres: Presidential; method: ImpactMethod }) {
  const blocs = (['far_right', 'centre_right', 'left', 'other'] as Bloc[]).filter((b) => (pres.blocs[b] ?? 0) > 0.0005)
  const expected = pres.market.expected_index_pct[method]
  return (
    <Panel className="mb-6">
      <SectionLabel>WHO WINS — BY POLITICAL BLOC</SectionLabel>
      <div className="flex w-full mb-3" style={{ height: 28 }}>
        {blocs.map((b) => (
          <div
            key={b}
            title={`${pres.bloc_labels[b]} ${pct(pres.blocs[b], 1)}`}
            style={{ width: `${pres.blocs[b] * 100}%`, background: BLOC_COLORS[b], display: 'flex', alignItems: 'center', paddingLeft: 8, overflow: 'hidden' }}
          >
            {pres.blocs[b] > 0.08 && (
              <span className="font-mono text-[11px] whitespace-nowrap" style={{ color: '#090909' }}>
                {pres.bloc_labels[b].toUpperCase()} {pct(pres.blocs[b])}
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2 items-baseline">
        {blocs.map((b) => (
          <span key={b} className="flex items-center gap-2 font-mono text-[11px]" style={{ color: '#929292' }}>
            <span style={{ width: 8, height: 8, background: BLOC_COLORS[b], display: 'inline-block' }} />
            {pres.bloc_labels[b]} <span style={{ color: '#F5F5F5' }}>{pct(pres.blocs[b], 1)}</span>
          </span>
        ))}
        <span className="font-mono text-[11px] ml-auto" style={{ color: '#929292' }}>
          PROBABILITY-WEIGHTED CAC40 IMPACT{' '}
          <span className="text-[14px]" style={{ color: impactColor(expected) }}>{signed(expected)}</span>
        </span>
      </div>
    </Panel>
  )
}

function CandidateTable({ pres }: { pres: Presidential }) {
  const rows = pres.candidates.filter((c) => c.poll_avg >= 1.5 || c.p_win > 0.001)
  const maxAvg = Math.max(...rows.map((c) => c.poll_avg))
  return (
    <Panel className="mb-6 overflow-x-auto">
      <SectionLabel>CANDIDATES — FIRST-ROUND POLLS AND SIMULATED OUTCOMES</SectionLabel>
      <table className="w-full" style={{ minWidth: 640 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #262626' }}>
            {['CANDIDATE', 'POLL AVG (RANGE)', 'IN LINE-UPS', 'REACH RUNOFF', 'WIN'].map((h) => (
              <th key={h} className="text-left pb-2 pr-4 font-mono text-[9px] tracking-widest" style={{ color: '#606060' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.key} style={{ borderBottom: '1px solid #1a1a1a' }}>
              <td className="py-2 pr-4">
                <div className="flex items-center gap-2">
                  <span style={{ width: 3, height: 26, background: BLOC_COLORS[c.bloc] }} />
                  <div>
                    <div className="text-[13px]" style={{ color: '#F5F5F5' }}>{c.full_name}</div>
                    <div className="font-mono text-[9px]" style={{ color: '#606060' }}>{c.party || '—'} · {c.bloc_label}</div>
                  </div>
                </div>
              </td>
              <td className="py-2 pr-4" style={{ width: 200 }}>
                <div className="flex items-center gap-2">
                  <Bar value={c.poll_avg} max={maxAvg} color={BLOC_COLORS[c.bloc]} />
                  <span className="font-mono text-[12px] tabular-nums w-10 text-right" style={{ color: '#F5F5F5' }}>{c.poll_avg.toFixed(1)}</span>
                  <span className="font-mono text-[9px] w-14" style={{ color: '#606060' }}>{c.poll_min}–{c.poll_max}</span>
                </div>
              </td>
              <td className="py-2 pr-4 font-mono text-[11px] tabular-nums" style={{ color: c.hypotheses_share < 0.9 ? '#FF9500' : '#929292' }}
                title="Share of recent poll line-ups that include this candidate. Below 100% means pollsters are unsure they will run.">
                {pct(c.hypotheses_share)}
              </td>
              <td className="py-2 pr-4" style={{ width: 150 }}>
                <div className="flex items-center gap-2">
                  <Bar value={c.p_runoff} color="#606060" />
                  <span className="font-mono text-[11px] tabular-nums w-10 text-right" style={{ color: '#929292' }}>{pct(c.p_runoff)}</span>
                </div>
              </td>
              <td className="py-2" style={{ width: 150 }}>
                <div className="flex items-center gap-2">
                  <Bar value={c.p_win} color="#F5F5F5" />
                  <span className="font-mono text-[12px] tabular-nums w-12 text-right" style={{ color: '#F5F5F5' }}>{pct(c.p_win, c.p_win < 0.1 ? 1 : 0)}</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="font-mono text-[9px] mt-3" style={{ color: '#3a3a3a' }}>
        IN LINE-UPS = share of recent poll hypotheses that include the candidate. Simulations draw a line-up, so candidacy uncertainty is part of the result.
      </div>
    </Panel>
  )
}

function Runoffs({ pres }: { pres: Presidential }) {
  return (
    <Panel>
      <SectionLabel>MOST LIKELY RUNOFFS</SectionLabel>
      {pres.matchups.slice(0, 6).map((m) => {
        const aShare = m.a_poll_share
        return (
          <div key={m.a + m.b} className="py-2" style={{ borderBottom: '1px solid #1a1a1a' }}>
            <div className="flex items-baseline justify-between mb-1.5">
              <span className="text-[12px]" style={{ color: '#F5F5F5' }}>{m.a} <span style={{ color: '#606060' }}>vs</span> {m.b}</span>
              <span className="font-mono text-[11px]" style={{ color: '#929292' }}>{pct(m.probability)} likely</span>
            </div>
            <div className="flex" style={{ height: 14 }}>
              <div style={{ width: `${aShare}%`, background: '#2a2a2a', display: 'flex', alignItems: 'center', paddingLeft: 4 }}>
                <span className="font-mono text-[9px]" style={{ color: '#F5F5F5' }}>{aShare.toFixed(0)}</span>
              </div>
              <div style={{ width: `${100 - aShare}%`, background: '#1a1a1a', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 4 }}>
                <span className="font-mono text-[9px]" style={{ color: '#929292' }}>{(100 - aShare).toFixed(0)}</span>
              </div>
            </div>
            <div className="font-mono text-[9px] mt-1" style={{ color: m.estimated ? '#FF9500' : '#3a3a3a' }}>
              {m.estimated ? 'NO HEAD-TO-HEAD POLL — ESTIMATED FROM SCORES VS RN' : 'HEAD-TO-HEAD POLL AVERAGE'} · {m.a} wins {pct(m.a_win_prob)} of these runoffs
            </div>
          </div>
        )
      })}
    </Panel>
  )
}

function PollTrend({ pres }: { pres: Presidential }) {
  const { dates, series, names } = pres.history
  const keys = Object.keys(series)
  const data = dates.map((d, i) => {
    const row: Record<string, string | number | null> = { date: d }
    keys.forEach((k) => { row[names[k] ?? k] = series[k][i] })
    return row
  })
  return (
    <Panel>
      <SectionLabel>FIRST-ROUND POLL TREND — 30-DAY ROLLING AVERAGE</SectionLabel>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#1a1a1a" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: '#606060', fontSize: 9, fontFamily: 'monospace' }} tickFormatter={(d: string) => d.slice(2, 7)} minTickGap={30} stroke="#262626" />
            <YAxis tick={{ fill: '#606060', fontSize: 9, fontFamily: 'monospace' }} stroke="#262626" unit="%" />
            <Tooltip contentStyle={{ background: '#101010', border: '1px solid #262626', fontSize: 11, fontFamily: 'monospace' }} labelStyle={{ color: '#929292' }} />
            <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'monospace' }} />
            {keys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={names[k] ?? k} stroke={SERIES_COLORS[i % SERIES_COLORS.length]} dot={false} strokeWidth={1.5} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  )
}

function MarketByWinner({ pres, method }: { pres: Presidential; method: ImpactMethod }) {
  const blocs: Bloc[] = ['far_right', 'centre_right', 'left']
  return (
    <div className="mb-6">
      <SectionLabel>IF THEY WIN — CAC40 IMPACT BY WINNING BLOC</SectionLabel>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {blocs.map((b) => {
          const imp = pres.market.bloc_impacts[b]
          const v = method === 'historical' ? imp?.historical_pct : imp?.factor_pct
          const movers = pres.market.movers[b]
          return (
            <Panel key={b}>
              <div className="flex items-center gap-2 mb-2">
                <span style={{ width: 8, height: 8, background: BLOC_COLORS[b] }} />
                <span className="text-[13px]" style={{ color: '#F5F5F5' }}>{pres.bloc_labels[b]}</span>
                <span className="font-mono text-[11px] ml-auto" style={{ color: '#929292' }}>P(win) {pct(pres.blocs[b], 1)}</span>
              </div>
              <div className="font-mono text-[26px] tabular-nums mb-1" style={{ color: impactColor(v) }}>{signed(v)}</div>
              <div className="font-mono text-[9px] mb-3" style={{ color: '#3a3a3a' }}>
                CAC40 · {method === 'historical' ? 'HISTORICAL ANALOG' : 'FACTOR MODEL'} · other method {signed(method === 'historical' ? imp?.factor_pct : imp?.historical_pct)}
              </div>
              {movers && (
                <div className="grid grid-cols-2 gap-3">
                  {(['worst', 'best'] as const).map((side) => (
                    <div key={side}>
                      <div className="font-mono text-[9px] tracking-widest mb-1" style={{ color: '#606060' }}>{side === 'worst' ? 'HIT HARDEST' : 'MOST RESILIENT'}</div>
                      {movers[side].map((m) => (
                        <div key={m.ticker} className="flex justify-between font-mono text-[10px] py-0.5">
                          <span style={{ color: '#929292' }} title={m.name}>{m.ticker.replace(/\.(PA|MI|AS)$/, '')}</span>
                          <span style={{ color: impactColor(m.impact_pct) }}>{signed(m.impact_pct)}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
              {movers && movers.method !== method && (
                <div className="font-mono text-[9px] mt-2" style={{ color: '#3a3a3a' }}>Movers use the {movers.method} method.</div>
              )}
            </Panel>
          )
        })}
      </div>
      <div className="font-mono text-[9px] mt-2" style={{ color: '#3a3a3a' }}>{pres.market.note}</div>
    </div>
  )
}

function Sparkline({ c }: { c: RiskComponent }) {
  const vals = c.series.map((p) => p.value)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const w = 220
  const h = 36
  const pts = vals.map((v, i) => `${(i / Math.max(vals.length - 1, 1)) * w},${h - ((v - min) / (max - min || 1)) * h}`).join(' ')
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ height: h, display: 'block' }}>
      <polyline points={pts} fill="none" stroke="#606060" strokeWidth={1} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

function StressGauge({ risk }: { risk: MarketRisk }) {
  const score = risk.composite.score
  const ref = risk.composite.reference_score
  const color = score >= 80 ? '#FF3B30' : score >= 60 ? '#FF9500' : score >= 40 ? '#929292' : '#34C759'
  const mc = risk.model_comparison
  return (
    <Panel className="mb-6">
      <SectionLabel right={<span className="font-mono text-[9px]" style={{ color: '#3a3a3a' }}>{risk.method}</span>}>
        WHAT MARKETS ARE PRICING — FRENCH POLITICAL STRESS GAUGE
      </SectionLabel>
      <div className="flex items-end gap-4 mb-2 flex-wrap">
        <div className="font-mono text-[34px] tabular-nums leading-none" style={{ color }}>{score.toFixed(0)}</div>
        <div className="font-mono text-[12px] pb-1" style={{ color }}>{risk.composite.label.toUpperCase()}</div>
        <div className="font-mono text-[10px] pb-1" style={{ color: '#606060' }}>/ 100 · {risk.composite.reference_label}: {ref?.toFixed(0) ?? '—'}</div>
      </div>
      <div style={{ position: 'relative', height: 8, background: 'linear-gradient(90deg,#1f3a24,#2a2a2a 45%,#3a2a12 70%,#3a1515)', marginBottom: 18 }}>
        <div style={{ position: 'absolute', left: `${score}%`, top: -4, width: 2, height: 16, background: '#F5F5F5' }} />
        {ref != null && (
          <div style={{ position: 'absolute', left: `${ref}%`, top: 10, transform: 'translateX(-50%)' }} className="font-mono text-[8px] whitespace-nowrap">
            <span style={{ color: '#929292' }}>▲ JUN 2024</span>
          </div>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {risk.components.map((c) => (
          <div key={c.id} className="p-3" style={{ border: '1px solid #1a1a1a' }}>
            <div className="flex justify-between items-baseline mb-1">
              <span className="font-mono text-[10px]" style={{ color: '#929292' }}>{c.label}</span>
              <span className="font-mono text-[9px]" style={{ color: '#606060' }}>P{c.percentile.toFixed(0)}</span>
            </div>
            <div className="font-mono text-[18px] tabular-nums" style={{ color: '#F5F5F5' }}>
              {c.unit === 'bp' ? `${c.value.toFixed(0)}bp` : signed(c.value)}
            </div>
            <Sparkline c={c} />
            <div className="font-mono text-[9px] mt-1" style={{ color: '#3a3a3a' }}>
              Jun 2024: {c.reference_value == null ? '—' : c.unit === 'bp' ? `${c.reference_value.toFixed(0)}bp` : signed(c.reference_value)}
              {' · '}worst {c.unit === 'bp' ? `${c.worst_value.toFixed(0)}bp` : signed(c.worst_value)} ({c.worst_date})
            </div>
            <div className="text-[10px] mt-1" style={{ color: '#606060' }}>{c.description}</div>
            <div className="font-mono text-[8px] mt-1" style={{ color: '#3a3a3a' }}>{c.source} · as of {c.as_of}</div>
          </div>
        ))}
      </div>
      <div className="p-3 text-[12px]" style={{ border: '1px solid #1a1a1a', color: '#929292' }}>
        <div className="font-mono text-[9px] tracking-widest mb-2" style={{ color: '#606060' }}>MODEL VS MARKET</div>
        Polls give the far right a <span style={{ color: '#F5F5F5' }}>{pct(mc.presidential_far_right_win)}</span> chance of the presidency, and the scenario blend puts
        disruptive outcomes (RN, left, hung parliament) at <span style={{ color: '#F5F5F5' }}>{pct(mc.blended_disruptive_probability)}</span>.
        The market gauge reads <span style={{ color }}>{risk.composite.label.toLowerCase()}</span> ({score.toFixed(0)}/100, versus {ref?.toFixed(0) ?? '—'} after the June 2024 dissolution).
        <div className="text-[10px] mt-2" style={{ color: '#606060' }}>{mc.note}</div>
      </div>
    </Panel>
  )
}

function Calendar({ events, source }: { events: CalendarEvent[]; source: string }) {
  return (
    <Panel>
      <SectionLabel right={<a href={source} target="_blank" rel="noopener noreferrer" className="font-mono text-[9px]" style={{ color: '#606060' }}>SOURCE</a>}>
        ELECTION CALENDAR
      </SectionLabel>
      <div>
        {events.map((e) => {
          const d = daysUntil(e.date)
          const past = d < 0
          return (
            <div key={e.date + e.title} className="flex gap-3 py-2" style={{ borderBottom: '1px solid #1a1a1a', opacity: past ? 0.55 : 1 }}>
              <div className="font-mono text-[10px] w-20 flex-shrink-0 tabular-nums" style={{ color: past ? '#606060' : '#F5F5F5' }}>{e.date}</div>
              <div className="flex-1 min-w-0">
                <div className="text-[12px]" style={{ color: past ? '#929292' : '#F5F5F5' }}>{e.title}</div>
                <div className="text-[10px]" style={{ color: '#606060' }}>{e.detail}</div>
              </div>
              <div className="font-mono text-[9px] flex-shrink-0" style={{ color: past ? '#3a3a3a' : '#D9A441' }}>
                {past ? 'PAST' : d === 0 ? 'TODAY' : `IN ${d}D`}
              </div>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

export default function ElectionPage() {
  const [pres, setPres] = useState<Presidential | null>(null)
  const [risk, setRisk] = useState<MarketRisk | null>(null)
  const [calendar, setCalendar] = useState<{ events: CalendarEvent[]; source: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [method, setMethod] = useState<ImpactMethod>('historical')

  useEffect(() => {
    api.getPresidential().then(setPres).catch((e: unknown) => setError(String(e)))
    api.getMarketRisk().then(setRisk).catch(() => null)
    api.getCalendar().then(setCalendar).catch(() => null)
  }, [])

  async function refresh() {
    setRefreshing(true)
    try {
      setPres(await api.refreshPresidential())
    } catch (e) {
      setError(String(e))
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Presidential Election 2027" />
      <div className="flex-1 p-6 overflow-auto">
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <div className="font-mono text-[11px] px-3 py-2 flex-1 min-w-[260px]" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
            POLL-BASED SIMULATION OF THE TWO-ROUND VOTE. MACRON CANNOT RUN. NOT A FORECAST OF CERTAINTY — SEE ASSUMPTIONS BELOW.
          </div>
          <div className="flex">
            {(['historical', 'factor'] as ImpactMethod[]).map((m) => (
              <button key={m} onClick={() => setMethod(m)} className="font-mono text-[10px] tracking-widest px-3 py-2"
                style={{ background: method === m ? '#1a1a1a' : 'transparent', border: '1px solid #262626', color: method === m ? '#F5F5F5' : '#606060' }}>
                {m === 'historical' ? 'HISTORICAL ANALOG' : 'FACTOR MODEL'}
              </button>
            ))}
          </div>
          <button onClick={refresh} disabled={refreshing} className="flex items-center gap-2 font-mono text-[10px] tracking-widest px-3 py-2"
            style={{ border: '1px solid #262626', color: '#929292', background: 'transparent' }}>
            <RefreshCw size={11} className={refreshing ? 'sys-spin' : ''} /> {refreshing ? 'FETCHING POLLS' : 'REFRESH POLLS'}
          </button>
        </div>

        {error && <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>{error}</div>}
        {pres && !pres.available && <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#929292', border: '1px solid #262626' }}>{pres.message}</div>}

        {pres?.available && (
          <>
            <Countdown pres={pres} />
            <BlocOverview pres={pres} method={method} />
            <CandidateTable pres={pres} />
            <MarketByWinner pres={pres} method={method} />
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 mb-6">
              <Runoffs pres={pres} />
              <PollTrend pres={pres} />
            </div>
          </>
        )}

        {risk?.available && <StressGauge risk={risk} />}

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 mb-6">
          {calendar && <Calendar events={calendar.events} source={calendar.source} />}
          {pres?.available && (
            <Panel>
              <SectionLabel>MODEL ASSUMPTIONS</SectionLabel>
              {Object.entries(pres.assumptions).map(([k, v]) => (
                <div key={k} className="flex gap-3 py-1.5" style={{ borderBottom: '1px solid #1a1a1a' }}>
                  <span className="font-mono text-[9px] uppercase w-40 flex-shrink-0" style={{ color: '#606060' }}>{k.replace(/_/g, ' ')}</span>
                  <span className="text-[11px]" style={{ color: '#929292' }}>{String(v)}</span>
                </div>
              ))}
              <div className="font-mono text-[9px] mt-3" style={{ color: '#3a3a3a' }}>
                Poll data: <a href={pres.source_url} target="_blank" rel="noopener noreferrer" style={{ color: '#606060' }}>French Wikipedia poll list</a> (CC BY-SA) ·
                {' '}{pres.n_first_round_polls_total} first-round polls and {pres.n_second_round_polls_total} head-to-head results parsed.
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
