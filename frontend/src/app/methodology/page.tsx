'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { MethodologyInfo } from '@/lib/types'
import { Header } from '@/components/layout/Header'
import { InfoTypeLabel } from '@/components/ui/InfoTypeLabel'

const INFO_TYPES = [
  { type: 'verified_fact', description: 'Supported by a traceable primary or reliable secondary source' },
  { type: 'reported_claim', description: 'Asserted by a source but not independently verified' },
  { type: 'model_interpretation', description: 'AI or analyst interpretation of available evidence' },
  { type: 'assumption', description: 'An explicit user or model input, not derived from data' },
  { type: 'scenario', description: 'A hypothetical state of the world used for analysis' },
  { type: 'forecast', description: 'A quantified estimate with a defined target, horizon, timestamp and methodology' },
]

const EVIDENCE_HIERARCHY = [
  'Official laws, government decisions, parliamentary records, ECB decisions, statistical releases',
  'Official party programmes and attributable speeches',
  'Reputable polling and established data providers',
  'Reputable news organizations',
  'Verified public statements on social platforms',
  'Unverified claims — remain unconfirmed',
]

const LIMITATIONS = [
  'Market prices fetched daily from Yahoo Finance — live prices shown per company and in heatmap drill-down',
  'Scenario probabilities auto-updated at startup from blended signals: Wikipedia polls + news VADER + Reddit + Google Trends',
  'AI news extraction runs automatically via Groq (llama-3.1-8b-instant) — only article text sent, no user data',
  'Revenue geography data sourced from 2023 annual reports — used to give each company unique scenario sensitivities',
  'Sector sensitivities calibrated against 2011 Eurozone crisis and 2022–23 ECB hiking cycle — not a live factor model',
  'Monte Carlo covariance estimated from 1 year of daily returns via Yahoo Finance — updated daily',
  'Portfolio supports equity instruments only — no derivatives or fixed income pricing',
  'Local use only — no production authentication or multi-user support',
]

export default function MethodologyPage() {
  const [info, setInfo] = useState<MethodologyInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getMethodology()
      .then(setInfo)
      .catch((e: unknown) => setError(String(e)))
  }, [])

  return (
    <div className="flex flex-col h-full">
      <Header title="Methodology & Model Audit" />

      <div className="flex-1 p-6 overflow-auto max-w-4xl">
        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        {/* Version banner */}
        <div className="mb-6 p-4 grid grid-cols-2 md:grid-cols-4 gap-4" style={{ background: '#101010', border: '1px solid #262626' }}>
          {[
            ['VERSION', info?.version ?? '0.1.0'],
            ['AI PROVIDER', info?.ai_provider ?? 'NONE (DETERMINISTIC)'],
            ['DATA CUTOFF', info?.data_cutoff ?? 'SEE INDIVIDUAL SOURCES'],
            ['ANALYSIS', info?.timestamp ? new Date(info.timestamp).toLocaleDateString('fr-FR') : new Date().toLocaleDateString('fr-FR')],
          ].map(([k, v]) => (
            <div key={k}>
              <div className="font-mono text-[10px] tracking-widest mb-1" style={{ color: '#606060' }}>{k}</div>
              <div className="font-mono text-[12px]" style={{ color: '#F5F5F5' }}>{v}</div>
            </div>
          ))}
        </div>

        {/* Information types */}
        <section className="mb-6">
          <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
            SIX INFORMATION TYPES
          </div>
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid #262626' }}>
                <th className="text-left pb-2 font-mono text-[10px] tracking-widest uppercase pr-6" style={{ color: '#606060' }}>
                  TYPE
                </th>
                <th className="text-left pb-2 font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>
                  DEFINITION
                </th>
              </tr>
            </thead>
            <tbody>
              {INFO_TYPES.map((it) => (
                <tr key={it.type} style={{ borderBottom: '1px solid #1a1a1a' }}>
                  <td className="py-3 pr-6 whitespace-nowrap">
                    <InfoTypeLabel type={it.type} />
                  </td>
                  <td className="py-3 text-[13px]" style={{ color: '#929292' }}>
                    {it.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Evidence hierarchy */}
        <section className="mb-6">
          <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
            EVIDENCE HIERARCHY (MOST → LEAST AUTHORITATIVE)
          </div>
          <ol className="space-y-2">
            {EVIDENCE_HIERARCHY.map((item, i) => (
              <li key={i} className="flex items-start gap-3 p-3" style={{ border: '1px solid #1a1a1a' }}>
                <span
                  className="flex-shrink-0 w-5 h-5 flex items-center justify-center font-mono text-[10px]"
                  style={{ color: '#606060', border: '1px solid #262626' }}
                >
                  {i + 1}
                </span>
                <span className="text-[13px]" style={{ color: '#929292' }}>{item}</span>
              </li>
            ))}
          </ol>
        </section>

        {/* Calculation */}
        <section className="mb-6">
          <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
            FINANCIAL CALCULATION METHOD
          </div>
          <div className="p-4 space-y-4" style={{ background: '#101010', border: '1px solid #262626' }}>
            {[
              {
                label: 'PORTFOLIO RETURN',
                formula: 'portfolio_return = Σ(w_i × r_i)',
                note: 'w_i = holding weight, r_i = scenario return for asset i',
              },
              {
                label: 'EXPECTED RETURN (SCENARIO-WEIGHTED)',
                formula: 'expected_return = Σ(p_s × R_s)',
                note: 'Requires scenarios to be exhaustive and mutually exclusive',
              },
              {
                label: 'PROBABILITY PROVENANCE',
                formula: null,
                note: 'Blended signal: 45% analyst prior + 15% Wikipedia election polls + 20% RSS news VADER sentiment + 10% Reddit r/france + 10% Google Trends party name search volume. Polymarket prediction markets override all signals when available.',
              },
            ].map(({ label, formula, note }) => (
              <div key={label} style={{ borderBottom: '1px solid #1a1a1a', paddingBottom: 12 }}>
                <div className="font-mono text-[10px] tracking-widest uppercase mb-1.5" style={{ color: '#606060' }}>
                  {label}
                </div>
                {formula && (
                  <code className="font-mono text-[12px] block mb-1" style={{ color: '#F5F5F5' }}>
                    {formula}
                  </code>
                )}
                <p className="text-[11px]" style={{ color: '#3a3a3a' }}>{note}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Model warnings */}
        {(info?.model_warnings?.length ?? 0) > 0 && (
          <section className="mb-6">
            <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
              MODEL WARNINGS
            </div>
            <div className="space-y-2">
              {info!.model_warnings.map((w, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 font-mono text-[11px] px-3 py-2"
                  style={{ color: '#FF9500', border: '1px solid #2a2000' }}
                >
                  <span>!</span> {w}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Limitations */}
        <section>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
            MVP LIMITATIONS
          </div>
          <ul className="space-y-1.5">
            {LIMITATIONS.map((lim, i) => (
              <li
                key={i}
                className="flex items-start gap-2 py-2.5 px-3"
                style={{ borderBottom: '1px solid #1a1a1a' }}
              >
                <span className="font-mono text-[10px] flex-shrink-0 mt-0.5" style={{ color: '#3a3a3a' }}>—</span>
                <span className="text-[13px]" style={{ color: '#929292' }}>{lim}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
