'use client'

import { useEffect, useMemo, useState, useCallback } from 'react'
import { ChevronDown, ChevronUp, X } from 'lucide-react'
import { api } from '@/lib/api'
import type { Scenario, Cac40Matrix, Cac40MatrixRow, EpisodeMeta, ImpactMethod, SentimentSignals } from '@/lib/types'
import { HistoryTab } from '@/components/scenarios/HistoryTab'
import { ReplayTab } from '@/components/scenarios/ReplayTab'
import { Header } from '@/components/layout/Header'

// --- Scenario imagery (Wikimedia Commons, CC-licensed) ---
const SCENARIO_IMAGES: Record<string, { url: string; caption: string; credit: string; source: string }> = {
  centrist: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Palais_de_l%27%C3%89lys%C3%A9e_2019.jpg/960px-Palais_de_l%27%C3%89lys%C3%A9e_2019.jpg',
    caption: 'Palais de l\'Élysée — continuity at the presidency',
    credit: 'Leynadmar · CC BY-SA 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:Palais_de_l%27%C3%89lys%C3%A9e_2019.jpg',
  },
  national_rally: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/2024-07-04_19-12-15_MeetingRN-Belfort.jpg/960px-2024-07-04_19-12-15_MeetingRN-Belfort.jpg',
    caption: 'Rassemblement National rally, Belfort, July 2024',
    credit: 'ComputerHotline · CC BY 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:2024-07-04_19-12-15_MeetingRN-Belfort.jpg',
  },
  left_wing: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Place_de_la_Bastille%2C_avril_2021.jpg/960px-Place_de_la_Bastille%2C_avril_2021.jpg',
    caption: 'Place de la Bastille — traditional gathering point of the French left',
    credit: 'Mododie · CC BY-SA 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:Place_de_la_Bastille,_avril_2021.jpg',
  },
  hung_parliament: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Hemicycle_assemblee_nationale.JPG/960px-Hemicycle_assemblee_nationale.JPG',
    caption: 'Hémicycle of the Assemblée nationale — no working majority',
    credit: 'Coucouoeuf · CC BY-SA 3.0',
    source: 'https://commons.wikimedia.org/wiki/File:Hemicycle_assemblee_nationale.JPG',
  },
}

function Spinner() {
  return (
    <div
      className="sys-spin"
      style={{ width: 14, height: 14, borderRadius: '50%', border: '1px solid #262626', borderTopColor: '#929292' }}
    />
  )
}

function signed(v: number | null | undefined, digits = 1): string {
  return v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
}

// --- Colour helpers ---
function impactColor(v: number): string {
  if (v >= 2) return '#34C759'
  if (v >= 0) return '#606060'
  if (v >= -5) return '#929292'
  if (v >= -10) return '#FF9500'
  return '#FF3B30'
}

function impactBg(v: number): string {
  if (v >= 3) return 'rgba(52,199,89,0.14)'
  if (v >= 1) return 'rgba(52,199,89,0.06)'
  if (v >= -1) return 'transparent'
  if (v >= -3) return 'rgba(255,149,0,0.07)'
  if (v >= -6) return 'rgba(255,59,48,0.09)'
  return 'rgba(255,59,48,0.18)'
}

// ─── Scenario row (scenarios tab) ────────────────────────────────────────────
function ScenarioRow({ s, index }: { s: Scenario; index: number }) {
  const [open, setOpen] = useState(false)
  const img = SCENARIO_IMAGES[s.name]

  return (
    <div style={{ borderBottom: '1px solid #262626' }}>
      {/* Collapsed header */}
      <div
        className="flex items-center gap-4 py-4 cursor-pointer"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={(e) => (e.currentTarget.style.background = '#101010')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        style={{ paddingRight: 8 }}
      >
        <div className="font-mono text-[10px] w-6 text-right flex-shrink-0" style={{ color: '#3a3a3a' }}>
          {String(index + 1).padStart(2, '0')}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium" style={{ color: '#F5F5F5' }}>{s.display_name}</div>
          <div className="text-[11px] mt-0.5 line-clamp-1" style={{ color: '#606060' }}>{s.description}</div>
        </div>
        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div style={{ width: 60, height: 2, background: '#262626', overflow: 'hidden' }}>
              <div style={{ width: `${s.probability * 100}%`, height: '100%', background: '#F5F5F5', transition: 'width 0.3s' }} />
            </div>
            <span className="font-mono text-[13px] w-10 text-right" style={{ color: '#F5F5F5' }}>
              {(s.probability * 100).toFixed(0)}%
            </span>
          </div>
          <div
            className="font-mono text-[10px] tracking-wide uppercase px-1.5 py-0.5 w-20 text-center"
            style={{ color: '#606060', border: '1px solid #262626', borderRadius: 2 }}
          >
            {s.implementation_feasibility?.toUpperCase() ?? 'UNKNOWN'}
          </div>
          <div style={{ color: '#606060' }}>
            {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </div>
        </div>
      </div>

      {/* Expanded detail */}
      {open && (
        <div className="pb-6 pl-10 pr-2" style={{ background: '#0d0d0d' }}>
          {/* Scenario image */}
          {img && (
            <div className="pt-4 mb-5">
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  maxWidth: 560,
                  height: 180,
                  overflow: 'hidden',
                  border: '1px solid #262626',
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img.url}
                  alt={img.caption}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'grayscale(30%) brightness(0.75)' }}
                  loading="lazy"
                  referrerPolicy="no-referrer"
                />
                <div
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    padding: '6px 10px',
                    background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
                    fontFamily: 'monospace',
                    fontSize: 10,
                    color: '#929292',
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                  }}
                >
                  <span>{img.caption}</span>
                  <a href={img.source} target="_blank" rel="noopener noreferrer" style={{ color: '#606060' }}>
                    {img.credit}
                  </a>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            {Object.keys(s.policy_assumptions ?? {}).length > 0 && (
              <div>
                <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>POLICY</div>
                {Object.entries(s.policy_assumptions ?? {}).map(([k, v]) => (
                  <div key={k} className="py-1.5 flex gap-3" style={{ borderBottom: '1px solid #1a1a1a' }}>
                    <span className="font-mono text-[10px] uppercase w-28 flex-shrink-0" style={{ color: '#606060' }}>{k}</span>
                    <span className="text-[12px]" style={{ color: '#929292' }}>{v}</span>
                  </div>
                ))}
              </div>
            )}
            {Object.keys(s.political_assumptions ?? {}).length > 0 && (
              <div>
                <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>POLITICAL</div>
                {Object.entries(s.political_assumptions ?? {}).map(([k, v]) => (
                  <div key={k} className="py-1.5 flex gap-3" style={{ borderBottom: '1px solid #1a1a1a' }}>
                    <span className="font-mono text-[10px] uppercase w-28 flex-shrink-0" style={{ color: '#606060' }}>{k}</span>
                    <span className="text-[12px]" style={{ color: '#929292' }}>{v}</span>
                  </div>
                ))}
              </div>
            )}
            {(s.invalidating_assumptions?.length ?? 0) > 0 && (
              <div className="md:col-span-2">
                <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>INVALIDATING CONDITIONS</div>
                {s.invalidating_assumptions.map((a, j) => (
                  <div key={j} className="py-1.5 flex gap-2" style={{ borderBottom: '1px solid #1a1a1a' }}>
                    <span className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>—</span>
                    <span className="text-[12px]" style={{ color: '#929292' }}>{a}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Company detail panel ─────────────────────────────────────────────────────
function CompanyDetail({ company, scenarios, episodes, method, onClose }: {
  company: Cac40MatrixRow
  scenarios: Cac40Matrix['scenarios']
  episodes: EpisodeMeta[]
  method: ImpactMethod
  onClose: () => void
}) {
  const sortedScenarios = [...scenarios].sort((a, b) =>
    (company.impacts[b.slug] ?? 0) - (company.impacts[a.slug] ?? 0)
  )

  return (
    <div
      style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 360,
        background: '#0d0d0d', borderLeft: '1px solid #262626',
        zIndex: 50, overflowY: 'auto', padding: 20,
      }}
    >
      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="font-mono text-[13px]" style={{ color: '#F5F5F5' }}>
            {company.ticker.replace(/\.(PA|MI|AS)$/, '')}
          </div>
          <div className="text-[12px] mt-0.5" style={{ color: '#929292' }}>{company.name}</div>
          <div className="font-mono text-[10px] mt-1" style={{ color: '#606060' }}>
            {company.sector}{company.subsector ? ` · ${company.subsector}` : ''}
          </div>
        </div>
        <button onClick={onClose} style={{ color: '#606060', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
          <X size={14} />
        </button>
      </div>

      {/* Live price + CAC40 weight */}
      <div className="mb-4 grid grid-cols-2 gap-2">
        <div className="p-3" style={{ background: '#101010', border: '1px solid #1a1a1a' }}>
          <div className="font-mono text-[9px] tracking-widest uppercase mb-1" style={{ color: '#3a3a3a' }}>LIVE PRICE</div>
          {company.live_price != null ? (
            <>
              <div className="font-mono text-[16px]" style={{ color: '#F5F5F5' }}>
                €{company.live_price.toFixed(2)}
              </div>
              <div className="font-mono text-[8px] mt-0.5" style={{ color: '#34C759' }}>LIVE · Yahoo Finance</div>
            </>
          ) : (
            <div className="font-mono text-[12px]" style={{ color: '#3a3a3a' }}>—</div>
          )}
        </div>
        <div className="p-3" style={{ background: '#101010', border: '1px solid #1a1a1a' }}>
          <div className="font-mono text-[9px] tracking-widest uppercase mb-1" style={{ color: '#3a3a3a' }}>CAC40 WEIGHT</div>
          <div className="font-mono text-[16px]" style={{ color: '#F5F5F5' }}>
            {company.cac_weight?.toFixed(1) ?? '—'}%
          </div>
        </div>
      </div>

      {/* Revenue geography */}
      <div className="mb-4">
        <div className="font-mono text-[9px] tracking-widest uppercase mb-2" style={{ color: '#3a3a3a' }}>REVENUE GEOGRAPHY (2023)</div>
        {[
          { label: 'France', pct: company.french_revenue_pct, color: '#4a90d9' },
          { label: 'Europe (ex-FR)', pct: 100 - (company.french_revenue_pct ?? 0) - (company.global_revenue_pct ?? 0), color: '#8b6dd9' },
          { label: 'Global', pct: company.global_revenue_pct, color: '#929292' },
        ].map(({ label, pct, color }) => (
          <div key={label} className="flex items-center gap-2 mb-1.5">
            <div className="font-mono text-[10px] w-24 flex-shrink-0" style={{ color: '#606060' }}>{label}</div>
            <div style={{ flex: 1, height: 4, background: '#1a1a1a' }}>
              <div style={{ width: `${pct ?? 0}%`, height: '100%', background: color }} />
            </div>
            <div className="font-mono text-[10px] w-8 text-right" style={{ color: '#929292' }}>{(pct ?? 0).toFixed(0)}%</div>
          </div>
        ))}
      </div>

      {/* Scenario impact breakdown */}
      <div className="mb-4">
        <div className="font-mono text-[9px] tracking-widest uppercase mb-2" style={{ color: '#3a3a3a' }}>
          SCENARIO IMPACTS · {method === 'historical' ? 'HISTORICAL ANALOG' : 'FACTOR MODEL'}
        </div>
        {sortedScenarios.map((sc) => {
          const v = company.impacts[sc.slug] ?? 0
          const barW = Math.min(Math.abs(v) / 20, 1) * 100
          return (
            <div key={sc.slug} className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px]" style={{ color: '#929292' }}>{sc.display_name}</span>
                <span className="font-mono text-[12px]" style={{ color: impactColor(v) }}>
                  {v >= 0 ? '+' : ''}{v.toFixed(2)}%
                </span>
              </div>
              <div style={{ position: 'relative', height: 4, background: '#1a1a1a' }}>
                <div style={{ width: `${barW}%`, height: '100%', background: v >= 0 ? '#34C759' : '#FF3B30', opacity: 0.8 }} />
              </div>
              <div className="font-mono text-[9px] mt-0.5" style={{ color: '#3a3a3a' }}>
                FACTOR <span style={{ color: method === 'factor' ? '#929292' : '#3a3a3a' }}>{signed(company.impacts_factor?.[sc.slug])}</span>
                {' · '}HISTORICAL <span style={{ color: method === 'historical' ? '#929292' : '#3a3a3a' }}>{signed(company.impacts_historical?.[sc.slug])}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Expected impact */}
      <div className="p-3" style={{ background: '#101010', border: '1px solid #1a1a1a' }}>
        <div className="font-mono text-[9px] tracking-widest uppercase mb-1" style={{ color: '#3a3a3a' }}>PROBABILITY-WEIGHTED EXPECTED</div>
        <div className="font-mono text-[18px]" style={{ color: impactColor(company.expected_impact_pct) }}>
          {company.expected_impact_pct >= 0 ? '+' : ''}{company.expected_impact_pct.toFixed(2)}%
        </div>
        <div className="font-mono text-[9px] mt-1" style={{ color: '#3a3a3a' }}>
          Weighted by current scenario probabilities. Not a forecast.
        </div>
      </div>

      {episodes.length > 0 && (
        <div className="mt-4">
          <div className="font-mono text-[9px] tracking-widest uppercase mb-2" style={{ color: '#3a3a3a' }}>
            REAL EPISODES — ACTUAL MOVE (DAX-ADJUSTED)
          </div>
          {episodes.map((e) => {
            const r = company.episode_returns?.[e.id]
            return (
              <div key={e.id} className="flex justify-between gap-3 py-1.5" style={{ borderBottom: '1px solid #1a1a1a' }}>
                <div className="min-w-0">
                  <div className="text-[11px]" style={{ color: '#929292' }}>{e.label}</div>
                  <div className="font-mono text-[9px]" style={{ color: '#3a3a3a' }}>{e.trading_start} → {e.trading_end}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="font-mono text-[11px]" style={{ color: r ? impactColor(r.raw_pct) : '#3a3a3a' }}>{r ? signed(r.raw_pct) : '—'}</div>
                  <div className="font-mono text-[9px]" style={{ color: '#606060' }}>{r ? `adj ${signed(r.abnormal_pct)}` : 'not listed'}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Weighted treemap heatmap ─────────────────────────────────────────────────
function WeightMap({ matrix, selectedSlug, method }: { matrix: Cac40Matrix; selectedSlug: string; method: ImpactMethod }) {
  const [selected, setSelected] = useState<Cac40MatrixRow | null>(null)

  const companies = [...matrix.companies].sort((a, b) => (b.cac_weight ?? 0) - (a.cac_weight ?? 0))
  const totalWeight = companies.reduce((s, c) => s + (c.cac_weight ?? 1), 0)

  function getImpact(c: Cac40MatrixRow): number {
    if (selectedSlug === 'all') return c.expected_impact_pct
    return c.impacts[selectedSlug] ?? 0
  }

  return (
    <div>
      {selected && (
        <CompanyDetail
          company={selected}
          scenarios={matrix.scenarios}
          episodes={matrix.episodes}
          method={method}
          onClose={() => setSelected(null)}
        />
      )}

      <div className="mb-3 font-mono text-[10px]" style={{ color: '#3a3a3a' }}>
        TILE SIZE = CAC40 INDEX WEIGHT · COLOUR = {selectedSlug === 'all' ? 'PROBABILITY-WEIGHTED EXPECTED IMPACT' : selectedSlug.toUpperCase().replace('_', ' ') + ' SCENARIO IMPACT'} · CLICK TO DRILL DOWN
      </div>

      {/* Treemap grid — flex-wrap, tile widths proportional to weight */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 2,
          alignContent: 'flex-start',
        }}
      >
        {companies.map((c) => {
          const v = getImpact(c)
          const weight = c.cac_weight ?? 1
          const minPx = 48
          const tilePx = Math.max(minPx, Math.round((weight / totalWeight) * 1200))
          const shortTicker = c.ticker.replace(/\.(PA|MI|AS)$/, '')

          return (
            <div
              key={c.ticker}
              onClick={() => setSelected(selected?.ticker === c.ticker ? null : c)}
              style={{
                width: tilePx,
                height: 54,
                background: impactBg(v),
                border: selected?.ticker === c.ticker
                  ? '1px solid #F5F5F5'
                  : '1px solid #1a1a1a',
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden',
                flexShrink: 0,
              }}
              onMouseEnter={(e) => { if (selected?.ticker !== c.ticker) e.currentTarget.style.borderColor = '#606060' }}
              onMouseLeave={(e) => { if (selected?.ticker !== c.ticker) e.currentTarget.style.borderColor = '#1a1a1a' }}
              title={`${c.name} — ${c.ticker}\n${v >= 0 ? '+' : ''}${v.toFixed(2)}% — CAC40 weight: ${(c.cac_weight ?? 0).toFixed(1)}%`}
            >
              <div style={{ padding: '4px 6px' }}>
                <div className="font-mono" style={{ fontSize: Math.max(8, Math.min(11, tilePx / 7)), color: '#F5F5F5', lineHeight: 1.2 }}>
                  {shortTicker}
                </div>
                <div className="font-mono tabular-nums" style={{ fontSize: Math.max(8, Math.min(12, tilePx / 6)), color: impactColor(v), lineHeight: 1.3 }}>
                  {v >= 0 ? '+' : ''}{v.toFixed(1)}%
                </div>
              </div>
              {/* Weight label for large tiles */}
              {tilePx >= 80 && (
                <div
                  style={{
                    position: 'absolute', bottom: 3, right: 5,
                    fontFamily: 'monospace', fontSize: 8, color: '#3a3a3a',
                  }}
                >
                  {(c.cac_weight ?? 0).toFixed(1)}%
                </div>
              )}
              {/* Bottom bar */}
              <div style={{
                position: 'absolute', bottom: 0, left: 0,
                width: `${Math.min(Math.abs(v) / 20, 1) * 100}%`,
                height: 2, background: v >= 0 ? '#34C759' : '#FF3B30', opacity: 0.6,
              }} />
            </div>
          )
        })}
      </div>

      <div className="mt-3 flex gap-4 flex-wrap font-mono text-[9px]" style={{ color: '#3a3a3a' }}>
        {[
          { color: '#34C759', label: '> +2%' },
          { color: '#606060', label: '0 to +2%' },
          { color: '#929292', label: '0 to −5%' },
          { color: '#FF9500', label: '−5% to −10%' },
          { color: '#FF3B30', label: '< −10%' },
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1">
            <span style={{ width: 8, height: 8, background: color, display: 'inline-block', borderRadius: 1 }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}

// ─── Tabular heatmap grid ─────────────────────────────────────────────────────
function HeatmapGrid({ matrix, method, onSelectCompany }: {
  matrix: Cac40Matrix
  method: ImpactMethod
  onSelectCompany: (c: Cac40MatrixRow) => void
}) {
  const [filterSector, setFilterSector] = useState('')
  const [sortBySlug, setSortBySlug] = useState<string>('all')

  const slugs = matrix.scenarios.map((s) => s.slug)
  const sectors = Array.from(new Set(matrix.companies.map((c) => c.sector))).sort()

  const bySector: Record<string, Cac40MatrixRow[]> = {}
  for (const c of matrix.companies) {
    if (!filterSector || c.sector === filterSector) {
      if (!bySector[c.sector]) bySector[c.sector] = []
      bySector[c.sector].push(c)
    }
  }

  function companyAvg(c: Cac40MatrixRow, slug?: string): number {
    if (slug && slug !== 'all') return c.impacts[slug] ?? 0
    return slugs.reduce((s, sl) => s + (c.impacts[sl] ?? 0), 0) / slugs.length
  }

  function sectorAvg(rows: Cac40MatrixRow[], slug: string): number {
    if (!rows.length) return 0
    return rows.reduce((s, r) => s + (r.impacts[slug] ?? 0), 0) / rows.length
  }

  const sectorOrder = Object.keys(bySector).sort(
    (a, b) =>
      bySector[a].reduce((s, r) => s + slugs.reduce((x, sl) => x + (r.impacts[sl] ?? 0), 0), 0) / (bySector[a].length * slugs.length) -
      bySector[b].reduce((s, r) => s + slugs.reduce((x, sl) => x + (r.impacts[sl] ?? 0), 0), 0) / (bySector[b].length * slugs.length)
  )

  const totalCompanies = Object.values(bySector).reduce((s, r) => s + r.length, 0)

  return (
    <div>
      <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
        {method === 'historical'
          ? 'HISTORICAL ANALOG — EACH STOCK’S ACTUAL MOVE VS THE DAX IN REAL FRENCH POLITICAL EPISODES, AVERAGED PER SCENARIO AND SCALED AS SHOWN IN EACH COLUMN.'
          : 'FACTOR MODEL — SECTOR SENSITIVITIES × ILLUSTRATIVE MACRO SHOCKS, SCALED BY EACH COMPANY’S REVENUE GEOGRAPHY.'}
      </div>

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <select
          value={filterSector}
          onChange={(e) => setFilterSector(e.target.value)}
          className="font-mono text-[11px] px-3 py-1.5 outline-none"
          style={{ background: '#101010', border: '1px solid #262626', borderRadius: 2, color: filterSector ? '#F5F5F5' : '#606060', appearance: 'none' }}
        >
          <option value="">ALL SECTORS</option>
          {sectors.map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}
        </select>

        <select
          value={sortBySlug}
          onChange={(e) => setSortBySlug(e.target.value)}
          className="font-mono text-[11px] px-3 py-1.5 outline-none"
          style={{ background: '#101010', border: '1px solid #262626', borderRadius: 2, color: '#929292', appearance: 'none' }}
        >
          <option value="all">SORT: OVERALL AVG</option>
          {matrix.scenarios.map((s) => (
            <option key={s.slug} value={s.slug}>SORT: {s.display_name.toUpperCase()}</option>
          ))}
        </select>

        <span className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>{totalCompanies} companies · click row to drill down</span>
      </div>

      {/* Column headers */}
      <div className="flex mb-1" style={{ borderBottom: '1px solid #262626' }}>
        <div className="flex-shrink-0 font-mono text-[9px] tracking-widest uppercase pb-2 pr-3" style={{ width: 180, color: '#3a3a3a' }}>
          COMPANY / {totalCompanies}
        </div>
        {matrix.scenarios.map((s) => (
          <div key={s.slug} className="flex-1 min-w-0 pb-2 px-2" style={{ borderLeft: '1px solid #1a1a1a' }}>
            <div className="font-mono text-[10px] tracking-wide uppercase" style={{ color: '#F5F5F5' }}>
              {s.display_name}
              {s.probability !== null && (
                <span className="ml-2 px-1 py-0.5 font-mono text-[9px]" style={{ color: '#606060', border: '1px solid #262626', borderRadius: 2 }}>
                  {(s.probability * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {method === 'historical' && matrix.analogs[s.slug] ? (
              <div className="font-mono text-[9px] mt-1" style={{ color: '#3a3a3a' }} title={matrix.analogs[s.slug].rationale}>
                {Object.values(matrix.analogs[s.slug].episode_labels).map((l) => <div key={l}>{l}</div>)}
                <div style={{ color: '#606060' }}>×{matrix.analogs[s.slug].scale} · {matrix.analogs[s.slug].confidence} confidence</div>
              </div>
            ) : (
              <div className="font-mono text-[9px] mt-1" style={{ color: '#3a3a3a' }}>
                <div>SPR <span style={{ color: '#606060' }}>+{s.macro_shocks.sovereign_spread_bps}bp</span></div>
                <div>EUR <span style={{ color: s.macro_shocks.eur_pct >= 0 ? '#34C759' : '#FF9500' }}>{s.macro_shocks.eur_pct >= 0 ? '+' : ''}{s.macro_shocks.eur_pct}%</span></div>
                <div>NRG <span style={{ color: s.macro_shocks.energy_pct >= 0 ? '#34C759' : '#FF9500' }}>{s.macro_shocks.energy_pct >= 0 ? '+' : ''}{s.macro_shocks.energy_pct}%</span></div>
              </div>
            )}
            <div className="font-mono text-[9px] mt-1" style={{ color: '#606060' }}>
              CAC40 <span style={{ color: impactColor(matrix.index_impact[method]?.[s.slug] ?? 0) }}>{signed(matrix.index_impact[method]?.[s.slug])}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Sector groups */}
      <div className="flex flex-col" style={{ gap: 1 }}>
        {sectorOrder.map((sector) => {
          const rawRows = bySector[sector]
          const rows = [...rawRows].sort((a, b) => companyAvg(a, sortBySlug) - companyAvg(b, sortBySlug))

          return (
            <div key={sector}>
              <div className="flex items-center" style={{ background: '#0a0a0a', borderTop: '1px solid #1a1a1a', borderBottom: '1px solid #1a1a1a' }}>
                <div className="flex-shrink-0 font-mono text-[9px] tracking-widest uppercase py-1.5 pr-3" style={{ width: 180, color: '#606060' }}>
                  {sector}
                </div>
                {slugs.map((slug) => {
                  const avg = sectorAvg(rawRows, slug)
                  return (
                    <div key={slug} className="flex-1 min-w-0 py-1.5 px-2 font-mono text-[9px] tabular-nums" style={{ borderLeft: '1px solid #1a1a1a', color: impactColor(avg) }}>
                      avg {avg >= 0 ? '+' : ''}{avg.toFixed(1)}%
                    </div>
                  )
                })}
              </div>

              {rows.map((c) => (
                <div
                  key={c.ticker}
                  className="flex"
                  style={{ borderBottom: '1px solid #0f0f0f', cursor: 'pointer' }}
                  onClick={() => onSelectCompany(c)}
                  onMouseEnter={(e) => (e.currentTarget.style.filter = 'brightness(1.15)')}
                  onMouseLeave={(e) => (e.currentTarget.style.filter = 'none')}
                >
                  <div className="flex-shrink-0 py-2 pr-3" style={{ width: 180, borderRight: '1px solid #1a1a1a' }}>
                    <div className="font-mono text-[11px]" style={{ color: '#F5F5F5' }}>
                      {c.ticker.replace(/\.(PA|MI|AS)$/, '')}
                      <span className="ml-2 font-mono text-[9px]" style={{ color: '#3a3a3a' }}>{(c.cac_weight ?? 0).toFixed(1)}%</span>
                    </div>
                    <div className="text-[10px] truncate hidden sm:block" style={{ color: '#606060' }} title={c.name}>{c.name}</div>
                  </div>

                  {slugs.map((slug) => {
                    const v = c.impacts[slug] ?? 0
                    return (
                      <div
                        key={slug}
                        className="flex-1 min-w-0 py-2 px-2"
                        style={{ position: 'relative', overflow: 'hidden', background: impactBg(v), borderLeft: '1px solid #1a1a1a' }}
                      >
                        <div className="font-mono text-[12px] tabular-nums font-medium" style={{ color: impactColor(v) }}>
                          {v >= 0 ? '+' : ''}{v.toFixed(1)}%
                        </div>
                        <div style={{ position: 'absolute', bottom: 0, left: 0, width: `${Math.min(Math.abs(v) / 20, 1) * 100}%`, height: 3, background: v >= 0 ? '#34C759' : '#FF3B30', opacity: 0.7 }} />
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )
        })}
      </div>

      <div className="flex gap-4 flex-wrap mt-4 font-mono text-[9px]" style={{ color: '#3a3a3a' }}>
        {[
          { color: '#34C759', label: '> +2%' },
          { color: '#606060', label: '0 to +2%' },
          { color: '#929292', label: '0 to −5%' },
          { color: '#FF9500', label: '−5% to −10%' },
          { color: '#FF3B30', label: '< −10%' },
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1">
            <span style={{ width: 8, height: 8, background: color, display: 'inline-block', borderRadius: 1 }} />
            {label}
          </span>
        ))}
        <span style={{ color: '#262626' }}>· WEIGHT % = CAC40 INDEX WEIGHT · BAR = IMPACT MAGNITUDE (MAX 20%)</span>
      </div>
      <div className="mt-2 font-mono text-[9px]" style={{ color: '#3a3a3a' }}>{matrix.disclaimer}</div>
    </div>
  )
}

// ─── Sentiment tab ────────────────────────────────────────────────────────────
function SentimentTab() {
  const [data, setData] = useState<SentimentSignals | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getSentimentSignals()
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const SCENARIO_NAMES: Record<string, string> = {
    centrist: 'Centrist',
    national_rally: 'National Rally',
    left_wing: 'Left Wing',
    hung_parliament: 'Hung Parliament',
  }

  const SOURCE_LABELS: Record<string, string> = {
    polls: 'Presidential poll simulation',
    news: 'News (Groq extraction / keywords)',
    reddit: 'Reddit',
    trends: 'Google Trends',
  }

  if (loading) return (
    <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
      <Spinner />
      <span className="font-mono text-[11px] tracking-widest uppercase">FETCHING SIGNALS</span>
    </div>
  )

  if (error) return (
    <div className="font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>{error}</div>
  )

  if (!data) return null

  const slugs = ['centrist', 'national_rally', 'left_wing', 'hung_parliament']
  const sources = Object.entries(data.sources)
  const activeCount = data.sources_active?.length ?? 0

  return (
    <div>
      <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
        BLENDED SIGNAL — {activeCount}/{sources.length} SOURCES ACTIVE · NOT AN ELECTION FORECAST
      </div>

      {/* Blended probability bars */}
      <div className="mb-6">
        <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>BLENDED SCENARIO PROBABILITIES</div>
        {slugs.map((slug) => {
          const pct = (data.probabilities[slug] ?? 0) * 100
          return (
            <div key={slug} className="flex items-center gap-3 mb-2">
              <div className="font-mono text-[11px] w-36 flex-shrink-0" style={{ color: '#929292' }}>
                {SCENARIO_NAMES[slug]}
              </div>
              <div style={{ flex: 1, height: 4, background: '#1a1a1a' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: '#F5F5F5', transition: 'width 0.5s' }} />
              </div>
              <div className="font-mono text-[12px] w-12 text-right tabular-nums" style={{ color: '#F5F5F5' }}>
                {pct.toFixed(1)}%
              </div>
            </div>
          )
        })}
      </div>

      {/* Source signals */}
      <div className="mb-5">
        <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>SOURCE SIGNALS</div>
        {sources.map(([key, src]) => (
          <div key={key} className="mb-4 p-3" style={{ border: '1px solid #1a1a1a' }}>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-[10px] tracking-wide uppercase" style={{ color: '#929292' }}>
                {SOURCE_LABELS[key] ?? key}
              </span>
              <span className="font-mono text-[9px]" style={{ color: '#606060' }}>WEIGHT {Math.round((src.weight ?? 0) * 100)}%</span>
              <span
                className="font-mono text-[9px] px-1.5 py-0.5"
                style={{
                  color: src.available ? '#34C759' : '#3a3a3a',
                  border: `1px solid ${src.available ? '#34C75933' : '#1a1a1a'}`,
                }}
              >
                {src.available ? 'ACTIVE' : 'UNAVAILABLE'}
              </span>
            </div>
            {src.available && Object.keys(src.signal).length > 0 && (
              <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                {slugs.map((slug) => {
                  const v = src.signal[slug]
                  if (v === undefined) return null
                  return (
                    <div key={slug} className="flex items-center gap-2">
                      <span className="font-mono text-[9px] w-28 flex-shrink-0" style={{ color: '#3a3a3a' }}>
                        {SCENARIO_NAMES[slug]}
                      </span>
                      <div style={{ flex: 1, height: 2, background: '#1a1a1a' }}>
                        <div style={{ width: `${Math.min(v * 100, 100)}%`, height: '100%', background: '#606060' }} />
                      </div>
                      <span className="font-mono text-[9px] w-8 text-right" style={{ color: '#606060' }}>
                        {(v * 100).toFixed(0)}%
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Methodology note */}
      <div className="font-mono text-[10px]" style={{ color: '#3a3a3a', borderTop: '1px solid #1a1a1a', paddingTop: 12 }}>
        {data.methodology}
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [matrix, setMatrix] = useState<Cac40Matrix | null>(null)
  const [matrixLoading, setMatrixLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'scenarios' | 'heatmap' | 'replay' | 'history' | 'sentiment'>('scenarios')
  const [method, setMethod] = useState<ImpactMethod>('factor')
  const [heatmapView, setHeatmapView] = useState<'grid' | 'weightmap'>('grid')
  const [weightSlug, setWeightSlug] = useState('all')
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)

  const handleSelectCompany = useCallback((c: Cac40MatrixRow) => {
    setSelectedTicker((prev) => (prev === c.ticker ? null : c.ticker))
  }, [])

  const viewMatrix = useMemo<Cac40Matrix | null>(() => {
    if (!matrix) return null
    return {
      ...matrix,
      companies: matrix.companies.map((c) => ({
        ...c,
        impacts_factor: c.impacts,
        impacts: method === 'historical' ? c.impacts_historical : c.impacts,
        expected_impact_pct: method === 'historical' ? (c.expected_impact_historical_pct ?? 0) : c.expected_impact_pct,
      })),
    }
  }, [matrix, method])
  const selectedCompany = viewMatrix?.companies.find((c) => c.ticker === selectedTicker) ?? null

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tab = params.get('tab')
    if (tab === 'scenarios' || tab === 'heatmap' || tab === 'replay' || tab === 'history' || tab === 'sentiment') setActiveTab(tab)
    const m = params.get('method')
    if (m === 'factor' || m === 'historical') setMethod(m)
  }, [])

  useEffect(() => {
    api.getScenarios()
      .then(setScenarios)
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false))

    api.getCac40Matrix()
      .then(setMatrix)
      .catch(() => null)
      .finally(() => setMatrixLoading(false))
  }, [])

  const probSum = scenarios.reduce((acc, s) => acc + s.probability, 0)

  return (
    <div className="flex flex-col h-full">
      <Header title="Political Scenarios" showDemoLabel />

      {/* Company drill-down panel */}
      {selectedCompany && viewMatrix && (
        <CompanyDetail
          company={selectedCompany}
          scenarios={viewMatrix.scenarios}
          episodes={viewMatrix.episodes}
          method={method}
          onClose={() => setSelectedTicker(null)}
        />
      )}

      <div className="flex-1 p-6 overflow-auto" style={{ paddingRight: selectedCompany ? 380 : 24 }}>
        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-0 mb-5" style={{ borderBottom: '1px solid #262626' }}>
          {([
            ['scenarios', 'SCENARIOS'],
            ['heatmap', 'IMPACT HEATMAP'],
            ['replay', 'REPLAY PAST SHOCKS'],
            ['history', 'PROBABILITY HISTORY'],
            ['sentiment', 'SIGNALS'],
          ] as const).map(([tab, label]) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="font-mono text-[11px] tracking-widest uppercase px-4 py-2"
              style={{
                color: activeTab === tab ? '#F5F5F5' : '#606060',
                borderBottom: activeTab === tab ? '1px solid #F5F5F5' : '1px solid transparent',
                marginBottom: -1,
                background: 'transparent',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── Scenarios tab ── */}
        {activeTab === 'scenarios' && (
          <>
            <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
              ANALYTICAL FRAMEWORKS — NOT PREDICTIONS. PROBABILITIES BLEND A FIXED ANALYST PRIOR WITH THE PRESIDENTIAL POLL SIMULATION AND NEWS SIGNALS (SEE SIGNALS TAB).
            </div>

            {Math.abs(probSum - 1) > 0.01 && scenarios.length > 0 && (
              <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
                PROBABILITY SUM = {(probSum * 100).toFixed(1)}% — MUST EQUAL 100%
              </div>
            )}

            {loading ? (
              <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
                <Spinner />
                <span className="font-mono text-[11px] tracking-widest uppercase">LOADING</span>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-4 pb-2" style={{ borderBottom: '1px solid #262626' }}>
                  <div className="w-6" />
                  <div className="flex-1 font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>SCENARIO</div>
                  <div className="flex items-center gap-4 flex-shrink-0">
                    <div className="font-mono text-[10px] tracking-widest uppercase w-[88px] text-right" style={{ color: '#606060' }}>PROBABILITY</div>
                    <div className="font-mono text-[10px] tracking-widest uppercase w-20 text-center" style={{ color: '#606060' }}>FEASIBILITY</div>
                    <div className="w-4" />
                  </div>
                </div>
                {scenarios.map((s, i) => (
                  <ScenarioRow key={s.id} s={s} index={i} />
                ))}
              </div>
            )}
          </>
        )}

        {/* ── Heatmap tab ── */}
        {activeTab === 'heatmap' && (
          matrixLoading ? (
            <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
              <Spinner />
              <span className="font-mono text-[11px] tracking-widest uppercase">LOADING HEATMAP</span>
            </div>
          ) : viewMatrix ? (
            <div>
              {/* Heatmap sub-nav */}
              <div className="flex items-center gap-3 mb-4 flex-wrap">
                <div className="flex mr-2">
                  {(['factor', 'historical'] as ImpactMethod[]).map((m) => (
                    <button
                      key={m}
                      onClick={() => setMethod(m)}
                      disabled={m === 'historical' && !viewMatrix.historical_available}
                      className="font-mono text-[10px] tracking-widest uppercase px-3 py-1.5"
                      style={{
                        background: method === m ? '#F5F5F5' : 'transparent',
                        color: method === m ? '#090909' : '#606060',
                        border: '1px solid #262626',
                        cursor: 'pointer',
                      }}
                      title={m === 'historical' && !viewMatrix.historical_available ? 'Historical data not computed yet' : undefined}
                    >
                      {m === 'factor' ? 'FACTOR MODEL' : 'HISTORICAL ANALOG'}
                    </button>
                  ))}
                </div>
                {(['grid', 'weightmap'] as const).map((v) => (
                  <button
                    key={v}
                    onClick={() => setHeatmapView(v)}
                    className="font-mono text-[10px] tracking-widest uppercase px-3 py-1.5"
                    style={{
                      background: heatmapView === v ? '#1a1a1a' : 'transparent',
                      border: `1px solid ${heatmapView === v ? '#262626' : '#1a1a1a'}`,
                      color: heatmapView === v ? '#F5F5F5' : '#606060',
                      cursor: 'pointer',
                      borderRadius: 2,
                    }}
                  >
                    {v === 'grid' ? 'TABLE GRID' : 'WEIGHT MAP'}
                  </button>
                ))}

                {heatmapView === 'weightmap' && (
                  <select
                    value={weightSlug}
                    onChange={(e) => setWeightSlug(e.target.value)}
                    className="font-mono text-[10px] px-3 py-1.5 outline-none"
                    style={{ background: '#101010', border: '1px solid #262626', borderRadius: 2, color: '#929292', appearance: 'none' }}
                  >
                    <option value="all">EXPECTED (PROB-WEIGHTED)</option>
                    {viewMatrix.scenarios.map((s) => (
                      <option key={s.slug} value={s.slug}>{s.display_name.toUpperCase()}</option>
                    ))}
                  </select>
                )}
              </div>

              {heatmapView === 'grid' ? (
                <HeatmapGrid matrix={viewMatrix} method={method} onSelectCompany={handleSelectCompany} />
              ) : (
                <WeightMap matrix={viewMatrix} selectedSlug={weightSlug} method={method} />
              )}
            </div>
          ) : (
            <div className="font-mono text-[11px] py-8" style={{ color: '#606060' }}>HEATMAP UNAVAILABLE</div>
          )
        )}

        {/* ── Sentiment tab ── */}
        {activeTab === 'replay' && <ReplayTab />}

        {activeTab === 'history' && <HistoryTab />}

        {activeTab === 'sentiment' && <SentimentTab />}
      </div>
    </div>
  )
}
