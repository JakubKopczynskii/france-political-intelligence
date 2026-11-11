'use client'

import { useRef, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Upload, Download, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { Portfolio } from '@/lib/types'
import { Header } from '@/components/layout/Header'

const CSV_TEMPLATE =
  'symbol,quantity,market_value,currency,asset_type\nAIR.PA,10,1500.00,EUR,equity\nBNP.PA,20,2400.00,EUR,equity\n'

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
        display: 'inline-block',
      }}
    />
  )
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const fileRef = useRef<HTMLInputElement>(null)

  const loadDemo = async () => {
    setLoading(true)
    setError(null)
    try {
      const p = await api.getDemoPortfolio()
      setPortfolio(p)
    } catch (e: unknown) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setValidationErrors(['FILE MUST BE .CSV'])
      return
    }
    setLoading(true)
    setValidationErrors([])
    setError(null)
    try {
      const p = await api.importPortfolio(file)
      setPortfolio(p)
    } catch (e: unknown) {
      const msg = String(e)
      if (msg.includes('422')) {
        setValidationErrors(['CSV VALIDATION FAILED — CHECK COLUMN NAMES AND DATA TYPES'])
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!portfolio) return
    if (!confirm('Delete portfolio data? This cannot be undone.')) return
    try {
      await api.deletePortfolioData(portfolio.id)
      setPortfolio(null)
    } catch (e: unknown) {
      setError(String(e))
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const downloadTemplate = () => {
    const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'portfolio_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const sectorData =
    portfolio?.holdings.reduce<Record<string, number>>((acc, h) => {
      const sec = h.sector ?? 'Unknown'
      acc[sec] = (acc[sec] ?? 0) + h.weight
      return acc
    }, {}) ?? {}

  const sectorChart = Object.entries(sectorData)
    .sort((a, b) => b[1] - a[1])
    .map(([sector, weight]) => ({ sector, weight: Math.round(weight * 100) }))

  return (
    <div className="flex flex-col h-full">
      <Header title="Portfolio" showDemoLabel={portfolio?.is_demo} />

      <div className="flex-1 p-6 overflow-auto">
        <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
          PORTFOLIO DATA STAYS LOCAL — NEVER SENT TO EXTERNAL SERVICES. EQUITY POSITIONS ONLY IN MVP.
        </div>

        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        {validationErrors.length > 0 && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {validationErrors.map((e, i) => (
              <div key={i}>{e}</div>
            ))}
          </div>
        )}

        {!portfolio ? (
          <div className="max-w-lg">
            <button
              onClick={loadDemo}
              disabled={loading}
              className="w-full py-3 font-mono text-[12px] tracking-widest uppercase disabled:opacity-40 flex items-center justify-center gap-2"
              style={{
                background: '#F5F5F5',
                color: '#090909',
                borderRadius: '2px',
              }}
            >
              {loading ? <><Spinner /> LOADING</> : 'LOAD DEMO PORTFOLIO'}
            </button>

            <div
              className="font-mono text-[10px] text-center my-4 tracking-widest"
              style={{ color: '#3a3a3a' }}
            >
              OR
            </div>

            <div
              className="p-8 text-center cursor-pointer transition-colors"
              style={{ border: '1px dashed #262626', borderRadius: '2px' }}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
              onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = '#606060')}
              onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = '#262626')}
            >
              <Upload className="w-6 h-6 mx-auto mb-3" style={{ color: '#3a3a3a' }} />
              <div className="font-mono text-[11px]" style={{ color: '#929292' }}>
                DRAG &amp; DROP CSV OR CLICK TO BROWSE
              </div>
              <div className="font-mono text-[10px] mt-1" style={{ color: '#3a3a3a' }}>
                COLUMNS: symbol · quantity · market_value · currency · asset_type
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) handleFile(f)
                }}
              />
            </div>

            <button
              onClick={downloadTemplate}
              className="mt-3 flex items-center gap-1.5 font-mono text-[10px] tracking-wide"
              style={{ color: '#606060' }}
            >
              <Download className="w-3 h-3" /> DOWNLOAD CSV TEMPLATE
            </button>
          </div>
        ) : (
          <>
            {/* Header row */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <div className="text-[15px] font-medium" style={{ color: '#F5F5F5' }}>
                  {portfolio.name}
                </div>
                <div className="font-mono text-[11px] mt-0.5" style={{ color: '#606060' }}>
                  {portfolio.holdings.length} HOLDINGS &nbsp;·&nbsp; €{portfolio.total_value.toLocaleString()} TOTAL
                  {portfolio.is_demo && (
                    <span className="ml-2 px-1.5 py-0.5" style={{ border: '1px solid #262626', color: '#606060' }}>
                      DEMO
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={handleDelete}
                className="flex items-center gap-1.5 font-mono text-[11px] tracking-wide uppercase"
                style={{ color: '#FF3B30' }}
              >
                <Trash2 className="w-3 h-3" /> DELETE
              </button>
            </div>

            {/* Sector bar */}
            {sectorChart.length > 0 && (
              <div className="mb-6">
                <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                  SECTOR EXPOSURE
                </div>
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
                          <Cell key={i} fill={i === 0 ? '#F5F5F5' : '#262626'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Holdings table */}
            <div>
              <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
                HOLDINGS
              </div>
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: '1px solid #262626' }}>
                    {['SYMBOL', 'NAME', 'WEIGHT', 'VALUE', 'SECTOR', 'TYPE'].map((h) => (
                      <th
                        key={h}
                        className="text-left pb-2 font-mono text-[10px] tracking-widest uppercase pr-4"
                        style={{ color: '#606060' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {portfolio.holdings.map((h) => (
                    <tr
                      key={h.symbol}
                      style={{ borderBottom: '1px solid #1a1a1a' }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#101010')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <td className="py-2.5 pr-4 font-mono text-[12px]" style={{ color: '#F5F5F5' }}>
                        {h.symbol}
                      </td>
                      <td className="py-2.5 pr-4 text-[13px]" style={{ color: '#929292' }}>
                        {h.company_name}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-[12px]" style={{ color: '#929292' }}>
                        {(h.weight * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-[12px]" style={{ color: '#929292' }}>
                        €{h.market_value.toLocaleString()}
                      </td>
                      <td className="py-2.5 pr-4 text-[12px]" style={{ color: '#606060' }}>
                        {h.sector ?? '—'}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-[11px]" style={{ color: '#3a3a3a' }}>
                        {h.asset_type.toUpperCase()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
