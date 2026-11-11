'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { ElectionExposure as Exposure, ImpactMethod } from '@/lib/types'

function signed(v: number | null | undefined, digits = 2) {
  return v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
}

function color(v: number | null | undefined) {
  if (v == null) return '#606060'
  if (v >= 0.5) return '#34C759'
  if (v >= -0.5) return '#929292'
  if (v >= -3) return '#FF9500'
  return '#FF3B30'
}

export function ElectionExposure({ portfolioId }: { portfolioId: number }) {
  const [data, setData] = useState<Exposure | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [method, setMethod] = useState<ImpactMethod>('historical')

  useEffect(() => {
    setData(null)
    api.getElectionExposure(portfolioId).then(setData).catch((e: unknown) => setError(String(e)))
  }, [portfolioId])

  if (error) return <div className="mt-6 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>{error}</div>
  if (!data) return null

  const m: ImpactMethod = data.methods.includes(method) ? method : data.methods[0]
  const sum = data.summary[m]
  if (!sum) return null
  const scenarios = data.scenarios

  return (
    <div className="mt-6 p-4" style={{ background: '#101010', border: '1px solid #262626' }}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>ELECTION EXPOSURE</div>
          <div className="text-[12px] mt-1" style={{ color: '#929292' }}>Estimated portfolio move if each political scenario happens. Computed locally — holdings are never sent anywhere.</div>
        </div>
        <div className="flex">
          {data.methods.map((x) => (
            <button key={x} onClick={() => setMethod(x)} className="font-mono text-[10px] tracking-widest px-3 py-1.5"
              style={{ background: m === x ? '#1a1a1a' : 'transparent', border: '1px solid #262626', color: m === x ? '#F5F5F5' : '#606060' }}>
              {x === 'historical' ? 'HISTORICAL ANALOG' : 'FACTOR MODEL'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-6 gap-2 mb-4">
        {scenarios.map((s) => {
          const v = sum.scenario_pct[s.slug]
          return (
            <div key={s.slug} className="p-3" style={{ border: `1px solid ${s.slug === sum.worst_scenario ? '#5a2a2a' : '#1a1a1a'}` }}>
              <div className="font-mono text-[9px] tracking-wide uppercase mb-1" style={{ color: '#606060' }}>{s.display_name}</div>
              <div className="font-mono text-[18px] tabular-nums" style={{ color: color(v) }}>{signed(v)}</div>
              <div className="font-mono text-[10px]" style={{ color: '#929292' }}>€{Math.round(sum.scenario_eur[s.slug]).toLocaleString('en-GB')}</div>
              <div className="font-mono text-[9px]" style={{ color: '#3a3a3a' }}>P {((s.probability ?? 0) * 100).toFixed(0)}%</div>
            </div>
          )
        })}
        <div className="p-3" style={{ border: '1px solid #262626', background: '#151515' }}>
          <div className="font-mono text-[9px] tracking-wide mb-1" style={{ color: '#606060' }}>SCENARIO-WEIGHTED</div>
          <div className="font-mono text-[18px] tabular-nums" style={{ color: color(sum.expected_pct) }}>{signed(sum.expected_pct)}</div>
          <div className="font-mono text-[9px]" style={{ color: '#3a3a3a' }}>blended probabilities</div>
        </div>
        <div className="p-3" style={{ border: '1px solid #262626', background: '#151515' }}>
          <div className="font-mono text-[9px] tracking-wide mb-1" style={{ color: '#606060' }}>POLL-WEIGHTED 2027</div>
          <div className="font-mono text-[18px] tabular-nums" style={{ color: color(sum.presidential_expected_pct) }}>{signed(sum.presidential_expected_pct)}</div>
          <div className="font-mono text-[9px]" style={{ color: '#3a3a3a' }}>presidential simulation</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-4">
        <div className="overflow-x-auto">
          <table className="w-full" style={{ minWidth: 560 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #262626' }}>
                <th className="text-left pb-2 pr-3 font-mono text-[9px] tracking-widest" style={{ color: '#606060' }}>HOLDING</th>
                <th className="text-left pb-2 pr-3 font-mono text-[9px] tracking-widest" style={{ color: '#606060' }}>WEIGHT</th>
                {scenarios.map((s) => (
                  <th key={s.slug} className="text-right pb-2 pr-3 font-mono text-[9px] tracking-widest" style={{ color: '#606060' }}>{s.display_name.split(' ')[0].toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.holdings.map((h) => (
                <tr key={h.symbol} style={{ borderBottom: '1px solid #1a1a1a' }}>
                  <td className="py-1.5 pr-3">
                    <div className="font-mono text-[11px]" style={{ color: '#F5F5F5' }}>{h.symbol}</div>
                    <div className="font-mono text-[9px]" style={{ color: h.basis.includes('proxy') ? '#FF9500' : '#3a3a3a' }}>{h.basis}</div>
                  </td>
                  <td className="py-1.5 pr-3 font-mono text-[11px]" style={{ color: '#929292' }}>{(h.weight * 100).toFixed(1)}%</td>
                  {scenarios.map((s) => {
                    const v = h.impacts[m]?.[s.slug] ?? null
                    return (
                      <td key={s.slug} className="py-1.5 pr-3 text-right font-mono text-[11px] tabular-nums" style={{ color: color(v) }}
                        title={`Contribution to portfolio: ${signed(h.contribution_pct[m]?.[s.slug])}`}>
                        {signed(v, 1)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-3" style={{ border: '1px solid #1a1a1a' }}>
          <div className="font-mono text-[9px] tracking-widest mb-2" style={{ color: '#606060' }}>
            BIGGEST DRAGS IN WORST CASE ({scenarios.find((s) => s.slug === sum.worst_scenario)?.display_name.toUpperCase()})
          </div>
          {sum.top_detractors.map((d) => (
            <div key={d.symbol} className="flex justify-between text-[11px] py-0.5">
              <span style={{ color: '#929292' }}>{d.name || d.symbol}</span>
              <span className="font-mono" style={{ color: color(d.contribution_pct) }}>{signed(d.contribution_pct)}</span>
            </div>
          ))}
          <div className="font-mono text-[9px] mt-2" style={{ color: '#3a3a3a' }}>Contribution = holding weight × holding impact.</div>
        </div>
      </div>
      <div className="font-mono text-[9px] mt-3" style={{ color: '#3a3a3a' }}>
        Non-CAC40 equities use a sector proxy (orange). {data.disclaimer}
      </div>
    </div>
  )
}
