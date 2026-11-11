'use client'

import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { api } from '@/lib/api'
import type { Company } from '@/lib/types'
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

const fmt = (v: number | null) =>
  v === null || v === undefined ? (
    <span style={{ color: '#3a3a3a' }}>—</span>
  ) : (
    <span className="font-mono">{v.toFixed(0)}%</span>
  )

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sector, setSector] = useState('')
  const [selected, setSelected] = useState<Company | null>(null)

  useEffect(() => {
    api.getCompanies()
      .then(setCompanies)
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const sectors = Array.from(new Set(companies.map((c) => c.sector))).sort()

  const filtered = companies.filter((c) => {
    const matchSearch =
      !search ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.ticker.toLowerCase().includes(search.toLowerCase())
    const matchSector = !sector || c.sector === sector
    return matchSearch && matchSector
  })

  return (
    <div className="flex flex-col h-full">
      <Header title="CAC 40 Universe" showDemoLabel />

      <div className="flex-1 p-6 overflow-auto">
        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
          REVENUE GEOGRAPHY: null = UNKNOWN, NOT ZERO. EXPOSURE DATA LABELLED SYNTHETIC WHERE APPLICABLE.
        </div>

        {/* Controls */}
        <div className="flex gap-3 mb-5">
          <input
            type="text"
            placeholder="SEARCH TICKER OR NAME"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="font-mono text-[11px] px-3 py-1.5 outline-none"
            style={{
              background: '#101010',
              border: '1px solid #262626',
              borderRadius: '2px',
              color: '#F5F5F5',
              width: 220,
            }}
          />
          <select
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            className="font-mono text-[11px] px-3 py-1.5 outline-none"
            style={{
              background: '#101010',
              border: '1px solid #262626',
              borderRadius: '2px',
              color: sector ? '#F5F5F5' : '#606060',
              appearance: 'none',
            }}
          >
            <option value="">ALL SECTORS</option>
            {sectors.map((s) => (
              <option key={s} value={s}>{s.toUpperCase()}</option>
            ))}
          </select>
          <span className="font-mono text-[10px] self-center" style={{ color: '#3a3a3a' }}>
            {filtered.length}/{companies.length}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
            <Spinner />
            <span className="font-mono text-[11px] tracking-widest uppercase">LOADING</span>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid #262626' }}>
                {['TICKER', 'NAME', 'SECTOR', 'SUBSECTOR', 'FR%', 'EU%', 'DATA'].map((h) => (
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
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="cursor-pointer"
                  onClick={() => setSelected(c)}
                  style={{ borderBottom: '1px solid #1a1a1a' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#101010')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td className="py-2.5 pr-4 font-mono text-[12px]" style={{ color: '#F5F5F5' }}>
                    {c.ticker}
                  </td>
                  <td className="py-2.5 pr-4 text-[13px]" style={{ color: '#929292' }}>
                    {c.name}
                  </td>
                  <td className="py-2.5 pr-4 text-[12px]" style={{ color: '#606060' }}>
                    {c.sector}
                  </td>
                  <td className="py-2.5 pr-4 text-[12px]" style={{ color: '#3a3a3a' }}>
                    {c.subsector ?? '—'}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]" style={{ color: '#929292' }}>
                    {fmt(c.french_revenue_pct)}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]" style={{ color: '#929292' }}>
                    {fmt(c.european_revenue_pct)}
                  </td>
                  <td className="py-2.5 pr-4">
                    {c.is_synthetic_exposure ? (
                      <span className="font-mono text-[9px] tracking-wide uppercase px-1.5 py-0.5" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
                        SYNTH
                      </span>
                    ) : (
                      <span className="font-mono text-[9px] tracking-wide uppercase px-1.5 py-0.5" style={{ color: '#34C759', border: '1px solid #1a2a1a' }}>
                        SRC
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail modal */}
      {selected && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: 'rgba(0,0,0,0.8)' }}
          onClick={() => setSelected(null)}
        >
          <div
            className="w-full max-w-lg p-6"
            style={{ background: '#101010', border: '1px solid #262626' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-5">
              <div>
                <div className="font-mono text-[12px]" style={{ color: '#929292' }}>
                  {selected.ticker}
                </div>
                <h2 className="text-[16px] font-medium mt-0.5" style={{ color: '#F5F5F5' }}>
                  {selected.name}
                </h2>
                <div className="font-mono text-[11px] mt-0.5" style={{ color: '#606060' }}>
                  {selected.sector}
                </div>
              </div>
              <button onClick={() => setSelected(null)} style={{ color: '#606060' }}>
                <X size={16} />
              </button>
            </div>
            {selected.is_synthetic_exposure && (
              <div className="mb-4 font-mono text-[10px] tracking-widest uppercase px-2 py-1.5" style={{ color: '#606060', border: '1px solid #262626' }}>
                SYNTHETIC EXPOSURE DATA
              </div>
            )}
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 font-mono text-[11px]">
              {[
                ['ISIN', selected.isin ?? '—'],
                ['INDEX', selected.index_member ?? '—'],
                ['CURRENCY', selected.listing_currency],
                ['SUBSECTOR', selected.subsector ?? '—'],
                ['FR REVENUE', selected.french_revenue_pct !== null ? `${selected.french_revenue_pct}%` : '—'],
                ['EU REVENUE', selected.european_revenue_pct !== null ? `${selected.european_revenue_pct}%` : '—'],
                ['GLOBAL REVENUE', selected.global_revenue_pct !== null ? `${selected.global_revenue_pct}%` : '—'],
                ['REVENUE SOURCE', selected.revenue_source ?? '—'],
              ].map(([k, v]) => (
                <div key={k}>
                  <div style={{ color: '#606060' }}>{k}</div>
                  <div className="mt-0.5" style={{ color: '#F5F5F5' }}>{v}</div>
                </div>
              ))}
            </div>
            {selected.data_quality_note && (
              <div className="mt-4 font-mono text-[10px]" style={{ color: '#3a3a3a' }}>
                {selected.data_quality_note}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
