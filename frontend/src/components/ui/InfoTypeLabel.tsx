'use client'

import type { InformationType } from '@/lib/types'

const LABEL: Record<InformationType, string> = {
  verified_fact: 'VERIFIED',
  reported_claim: 'REPORTED',
  model_interpretation: 'MODEL',
  assumption: 'ASSUMPTION',
  scenario: 'SCENARIO',
  forecast: 'FORECAST',
}

export function InfoTypeLabel({
  type,
  className = '',
}: {
  type: InformationType | string
  className?: string
}) {
  const label = LABEL[type as InformationType] ?? type.toUpperCase()
  const isVerified = type === 'verified_fact'

  return (
    <span
      className={`font-mono text-[10px] tracking-widest uppercase px-1.5 py-0.5 ${className}`}
      style={{
        color: isVerified ? '#F5F5F5' : '#606060',
        border: `1px solid ${isVerified ? '#606060' : '#262626'}`,
        borderRadius: '2px',
      }}
    >
      {label}
    </span>
  )
}
