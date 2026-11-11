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
  ReferenceLine,
} from 'recharts'
import { api } from '@/lib/api'
import type { Portfolio, ShockInputs, StressTestResult } from '@/lib/types'
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

function ShockSlider({
  label,
  unit,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string
  unit: string
  min: number
  max: number
  step: number
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="font-mono text-[11px] tracking-wide uppercase" style={{ color: '#929292' }}>
          {label}
        </span>
        <span className="font-mono text-[12px]" style={{ color: '#F5F5F5' }}>
          {value > 0 ? '+' : ''}{value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
        style={{ accentColor: '#F5F5F5' }}
      />
      <div className="flex justify-between mt-0.5 font-mono text-[9px]" style={{ color: '#3a3a3a' }}>
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  )
}

const DEFAULT_SHOCKS: ShockInputs = {
  sovereign_spread: 50,
  eur: 0,
  ecb_rate: 25,
  energy: 0,
}

export default function StressTestPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [shocks, setShocks] = useState<ShockInputs>(DEFAULT_SHOCKS)
  const [result, setResult] = useState<StressTestResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getDemoPortfolio().then(setPortfolio).catch(() => null)
  }, [])

  const setShock = (key: keyof ShockInputs) => (v: number) => {
    setShocks((p) => ({ ...p, [key]: v }))
  }

  const run = async () => {
    if (!portfolio) {
      setError('No portfolio loaded — go to Portfolio screen to load one')
      return
    }
    setRunning(true)
    setError(null)
    try {
      const res = await api.runStressTest({
        portfolio_id: portfolio.id,
        shocks,
        methodology: 'linear',
      })
      setResult(res)
    } catch (e: unknown) {
      setError(String(e))
    } finally {
      setRunning(false)
    }
  }

  const pnlPositive = result ? result.portfolio_pnl_pct >= 0 : false

  const holdingChart =
    result?.holding_contributions
      .map((h) => ({
        symbol: h.symbol,
        pnl: Math.round(h.pnl_pct * 100) / 100,
      }))
      .sort((a, b) => a.pnl - b.pnl) ?? []

  const sectorChart =
    result?.sector_contributions
      .map((s) => ({
        sector: s.sector,
        pnl: Math.round(s.pnl_pct * 100) / 100,
      }))
      .sort((a, b) => a.pnl - b.pnl) ?? []

  return (
    <div className="flex flex-col h-full">
      <Header title="Stress Testing" />

      <div className="flex-1 p-6 overflow-auto">
        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
          HYPOTHETICAL STRESS INPUTS — NOT A FORECAST. IMPACT = Σ(WEIGHT × SENSITIVITY × SHOCK).
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Shock inputs */}
          <div className="p-5" style={{ border: '1px solid #262626', background: '#101010' }}>
            <div className="font-mono text-[10px] tracking-widest uppercase mb-5" style={{ color: '#606060' }}>
              SHOCK INPUTS
            </div>
            <div className="space-y-5">
              <ShockSlider
                label="Sovereign spread"
                unit=" bps"
                min={0}
                max={300}
                step={10}
                value={shocks.sovereign_spread}
                onChange={setShock('sovereign_spread')}
              />
              <ShockSlider
                label="EUR shock"
                unit="%"
                min={-10}
                max={10}
                step={1}
                value={shocks.eur}
                onChange={setShock('eur')}
              />
              <ShockSlider
                label="ECB rate shock"
                unit=" bps"
                min={0}
                max={200}
                step={25}
                value={shocks.ecb_rate}
                onChange={setShock('ecb_rate')}
              />
              <ShockSlider
                label="Energy shock"
                unit="%"
                min={-30}
                max={30}
                step={5}
                value={shocks.energy}
                onChange={setShock('energy')}
              />
            </div>
            <button
              onClick={run}
              disabled={running}
              className="mt-6 w-full py-2.5 font-mono text-[12px] tracking-widest uppercase disabled:opacity-40"
              style={{
                background: running ? '#262626' : '#F5F5F5',
                color: '#090909',
                border: '1px solid #F5F5F5',
                cursor: running ? 'not-allowed' : 'pointer',
              }}
            >
              {running ? (
                <span className="flex items-center justify-center gap-2">
                  <Spinner /> CALCULATING
                </span>
              ) : 'RUN STRESS TEST'}
            </button>
            {!portfolio && (
              <p className="mt-2 font-mono text-[10px] text-center" style={{ color: '#FF9500' }}>
                NO PORTFOLIO — GO TO PORTFOLIO SCREEN
              </p>
            )}
          </div>

          {/* Results */}
          <div className="lg:col-span-2 space-y-4">
            {result ? (
              <>
                {/* P&L summary */}
                <div className="p-5" style={{ border: '1px solid #262626', background: '#101010' }}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>
                      PORTFOLIO P&amp;L
                    </span>
                    <span className="font-mono text-[10px] tracking-wide" style={{ color: '#3a3a3a' }}>
                      DETERMINISTIC · LINEAR FACTOR
                    </span>
                  </div>
                  <div
                    className="font-mono text-[36px] font-medium leading-none"
                    style={{ color: pnlPositive ? '#34C759' : '#FF3B30' }}
                  >
                    {result.portfolio_pnl_pct >= 0 ? '+' : ''}
                    {result.portfolio_pnl_pct.toFixed(2)}%
                  </div>
                  <div
                    className="font-mono text-[16px] mt-1"
                    style={{ color: pnlPositive ? '#34C759' : '#FF3B30' }}
                  >
                    {result.portfolio_pnl_eur >= 0 ? '+' : ''}€
                    {result.portfolio_pnl_eur.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-4">
                    {([
                      ['BEST', result.best_holding, '#34C759'],
                      ['WORST', result.worst_holding, '#FF3B30'],
                      ['METHOD', result.methodology, '#929292'],
                    ] as [string, string, string][]).map(([label, val, color]) => (
                      <div key={label}>
                        <div className="font-mono text-[9px] tracking-widest mb-1" style={{ color: '#606060' }}>
                          {label}
                        </div>
                        <div className="font-mono text-[11px]" style={{ color }}>
                          {val || '—'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Holding contributions chart */}
                {holdingChart.length > 0 && (
                  <div className="p-5" style={{ border: '1px solid #262626', background: '#101010' }}>
                    <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                      HOLDING CONTRIBUTIONS
                    </div>
                    <div style={{ height: 220 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={holdingChart} layout="vertical" margin={{ left: 4, right: 8 }}>
                          <XAxis
                            type="number"
                            tick={{ fill: '#606060', fontSize: 10, fontFamily: 'monospace' }}
                            unit="%"
                            axisLine={false}
                            tickLine={false}
                          />
                          <YAxis
                            type="category"
                            dataKey="symbol"
                            tick={{ fill: '#606060', fontSize: 10, fontFamily: 'monospace' }}
                            width={60}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Tooltip
                            contentStyle={{
                              background: '#101010',
                              border: '1px solid #262626',
                              borderRadius: 0,
                              fontSize: 11,
                              fontFamily: 'monospace',
                              color: '#F5F5F5',
                            }}
                            formatter={(v: unknown) => [`${v as number}%`, 'P&L']}
                          />
                          <ReferenceLine x={0} stroke="#262626" />
                          <Bar dataKey="pnl" radius={0}>
                            {holdingChart.map((e, i) => (
                              <Cell key={i} fill={e.pnl >= 0 ? '#34C759' : '#FF3B30'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Sector contributions chart */}
                {sectorChart.length > 0 && (
                  <div className="p-5" style={{ border: '1px solid #262626', background: '#101010' }}>
                    <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                      SECTOR CONTRIBUTIONS
                    </div>
                    <div style={{ height: 160 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={sectorChart} layout="vertical" margin={{ left: 4, right: 8 }}>
                          <XAxis
                            type="number"
                            tick={{ fill: '#606060', fontSize: 10, fontFamily: 'monospace' }}
                            unit="%"
                            axisLine={false}
                            tickLine={false}
                          />
                          <YAxis
                            type="category"
                            dataKey="sector"
                            tick={{ fill: '#606060', fontSize: 10, fontFamily: 'monospace' }}
                            width={90}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Tooltip
                            contentStyle={{
                              background: '#101010',
                              border: '1px solid #262626',
                              borderRadius: 0,
                              fontSize: 11,
                              fontFamily: 'monospace',
                              color: '#F5F5F5',
                            }}
                            formatter={(v: unknown) => [`${v as number}%`, 'P&L']}
                          />
                          <ReferenceLine x={0} stroke="#262626" />
                          <Bar dataKey="pnl" radius={0}>
                            {sectorChart.map((e, i) => (
                              <Cell key={i} fill={e.pnl >= 0 ? '#34C759' : '#FF3B30'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Disclaimer */}
                <div className="font-mono text-[9px] px-1" style={{ color: '#3a3a3a' }}>
                  {result.disclaimer}
                </div>
              </>
            ) : (
              <div
                className="p-8 text-center font-mono text-[11px]"
                style={{ border: '1px solid #262626', color: '#606060' }}
              >
                CONFIGURE SHOCKS AND CLICK RUN STRESS TEST TO SEE RESULTS
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
