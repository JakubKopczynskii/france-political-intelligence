'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { ECBScenario } from '@/lib/types'
import { Header } from '@/components/layout/Header'
import { InfoTypeLabel } from '@/components/ui/InfoTypeLabel'

const CHANNELS = [
  { channel: 'POLICY RATE', description: 'Direct effect on borrowing costs across the economy' },
  { channel: 'EUR EXCHANGE RATE', description: 'Euro strength/weakness affects exporters and importers' },
  { channel: 'OAT-BUND SPREAD', description: 'French sovereign risk premium vs German benchmark' },
  { channel: 'BANK NET INTEREST MARGIN', description: 'Higher rates expand margins; lower rates compress them' },
  { channel: 'UTILITY DISCOUNT RATE', description: 'DCF valuations sensitive to risk-free rate changes' },
  { channel: 'REAL ESTATE CAP RATES', description: 'Property valuations move inversely with rates' },
]

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

function ImpactRow({ label, value, unit }: { label: string; value: number; unit: string }) {
  const positive = value >= 0
  return (
    <div className="flex justify-between items-center py-2" style={{ borderBottom: '1px solid #1a1a1a' }}>
      <span className="font-mono text-[10px] tracking-wide uppercase" style={{ color: '#606060' }}>{label}</span>
      <span
        className="font-mono text-[12px]"
        style={{ color: positive ? '#34C759' : '#FF3B30' }}
      >
        {positive ? '+' : ''}{value}{unit}
      </span>
    </div>
  )
}

export default function ECBPage() {
  const [scenarios, setScenarios] = useState<ECBScenario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getECBScenarios()
      .then(setScenarios)
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full">
      <Header title="ECB Module" showDemoLabel />

      <div className="flex-1 p-6 overflow-auto">
        <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
          HYPOTHETICAL PROFILES — NOT PREDICTIONS. SCENARIO EXERCISE AROUND ECB LEADERSHIP SUCCESSION.
          NO SUCCESSOR IS ASSUMED OR NAMED. THIS MODULE IS SEPARATE FROM FRENCH POLITICAL SCENARIOS.
        </div>

        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        {/* Scenario grid */}
        <div className="mb-8">
          <div className="font-mono text-[10px] tracking-widest uppercase mb-4" style={{ color: '#606060' }}>
            LAGARDE SUCCESSION — POLICY PROFILE SCENARIOS
          </div>

          {loading ? (
            <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
              <Spinner />
              <span className="font-mono text-[11px] tracking-widest uppercase">LOADING</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {scenarios.map((s) => (
                <div
                  key={s.id}
                  className="p-4 flex flex-col gap-3"
                  style={{ background: '#101010', border: '1px solid #262626' }}
                >
                  <div>
                    <div className="text-[13px] font-medium capitalize" style={{ color: '#F5F5F5' }}>
                      {s.profile_name}
                    </div>
                    <p className="text-[11px] mt-1 leading-relaxed" style={{ color: '#606060' }}>
                      {s.description}
                    </p>
                  </div>

                  <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 8 }}>
                    <ImpactRow label="RATE Δ" value={s.policy_rate_delta_bps} unit=" bps" />
                    <ImpactRow label="EUR IMPACT" value={s.eur_impact_pct} unit="%" />
                    <ImpactRow label="OAT-BUND Δ" value={s.oat_bund_spread_delta_bps} unit=" bps" />
                    <ImpactRow label="BANK MARGIN" value={s.bank_margin_impact_pct} unit="%" />
                  </div>

                  <div className="mt-auto pt-2">
                    <InfoTypeLabel type={s.is_verified_fact ? 'verified_fact' : 'assumption'} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Transmission channels */}
        <div>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-3" style={{ color: '#606060' }}>
            MONETARY POLICY TRANSMISSION CHANNELS
          </div>
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid #262626' }}>
                <th className="text-left pb-2 font-mono text-[10px] tracking-widest uppercase pr-6" style={{ color: '#606060' }}>
                  CHANNEL
                </th>
                <th className="text-left pb-2 font-mono text-[10px] tracking-widest uppercase" style={{ color: '#606060' }}>
                  MECHANISM
                </th>
              </tr>
            </thead>
            <tbody>
              {CHANNELS.map((c) => (
                <tr key={c.channel} style={{ borderBottom: '1px solid #1a1a1a' }}>
                  <td className="py-3 pr-6 font-mono text-[11px] whitespace-nowrap" style={{ color: '#F5F5F5' }}>
                    {c.channel}
                  </td>
                  <td className="py-3 text-[13px]" style={{ color: '#606060' }}>
                    {c.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
